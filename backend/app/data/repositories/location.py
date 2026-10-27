"""LocationRepository(COMP-12): 근접·조건 검색, 촬영지 조회, 관리자 속성 편집."""

from dataclasses import replace

from pgvector import Vector
from psycopg_pool import AsyncConnectionPool

from app.data.models import (
    Conditions,
    CourseCandidate,
    DictHit,
    Location,
    LocationAttrs,
    LocationHit,
    Photo,
    Point,
    WorkHit,
)
from app.data.repositories import templates
from app.data.repositories._rows import build

_LOCATION_COLS = (
    "id, name, address, gu, lat, lon, tags, caution, safety_note, cert_radius_m, cert_excluded,"
    " nearest_station_id, station_walk_min"
)


class LocationRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def _run(self, sql: str, params: dict) -> list[dict]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchall()

    async def search(self, cond: Conditions, limit: int = templates.MAX_LIMIT) -> list[LocationHit] | list[WorkHit]:
        """조건으로 T1~T4 중 하나를 골라 실행한다. result_type이 WORK면 WorkHit을 돌려준다."""
        sql, params = templates.choose(cond, limit)
        rows = await self._run(sql, params)
        cls = WorkHit if cond.result_type == "WORK" else LocationHit
        return [build(cls, r) for r in rows]

    async def within_radius(
        self, base: Point, radius_m: int, filters: Conditions | None = None, limit: int = templates.MAP_MAX_LIMIT
    ) -> list[LocationHit]:
        """지도 홈 근접 검색(API-005, FR-203). 좌표 없는 촬영지는 빠진다(FR-210)."""
        cond = replace(filters or Conditions(), point=base, radius_m=float(radius_m), result_type="LOCATION")
        sql, params = templates.choose(cond, limit, max_limit=templates.MAP_MAX_LIMIT)
        return [build(LocationHit, r) for r in await self._run(sql, params)]

    async def get(self, location_id: int) -> Location | None:
        rows = await self._run(
            f"SELECT {_LOCATION_COLS} FROM location WHERE id = %(id)s AND NOT retired", {"id": location_id}
        )
        return build(Location, rows[0]) if rows else None

    async def update_attrs(self, location_id: int, attrs: LocationAttrs) -> Location | None:
        """관리자 편집(FR-610). 동기화(publish)는 이 열들을 덮어쓰지 않는다(build-plan 7장)."""
        rows = await self._run(
            "UPDATE location SET"
            " caution = COALESCE(%(caution)s, caution),"
            " safety_note = COALESCE(%(safety_note)s, safety_note),"
            " cert_radius_m = COALESCE(%(cert_radius_m)s, cert_radius_m),"
            " cert_excluded = COALESCE(%(cert_excluded)s, cert_excluded)"
            f" WHERE id = %(id)s AND NOT retired RETURNING {_LOCATION_COLS}",
            {"id": location_id, **attrs.__dict__},
        )
        return build(Location, rows[0]) if rows else None

    async def photo(self, location_id: int) -> Photo | None:
        """장소 사진 한 장(공공누리 제1유형만 저장됨, BR-03)."""
        rows = await self._run(
            "SELECT url, title, source_id FROM photo WHERE location_id = %(id)s ORDER BY id LIMIT 1",
            {"id": location_id},
        )
        return build(Photo, rows[0]) if rows else None

    async def by_name(self, text: str, k: int = 3) -> list[DictHit]:
        """장소 이름 트라이그램 대조(기준 장소 '«장소» 근처', FR-402). 좌표가 있는 장소만."""
        rows = await self._run(
            "SELECT 'location' AS kind, name AS surface, id::text AS canonical_id,"
            " similarity(name, %(q)s) AS score FROM location"
            " WHERE NOT retired AND lat IS NOT NULL ORDER BY score DESC, id LIMIT %(k)s",
            {"q": text, "k": k},
        )
        return [build(DictHit, r) for r in rows]

    async def course_candidates(self, vec: list[float] | None = None) -> list[CourseCandidate]:
        """좌표가 있는 촬영지 전부와 작품 장르·인물·작품 수, 취향 벡터와의 유사도(벡터가 있을 때)."""
        sim = "1 - (l.embedding <=> %(vec)s::vector)" if vec is not None else "NULL::float8"
        rows = await self._run(
            f"SELECT l.id, l.name, l.lat, l.lon, l.gu, l.tags, l.caution, l.nearest_station_id, l.station_walk_min,"
            " COALESCE(array_agg(DISTINCT g) FILTER (WHERE g IS NOT NULL), '{}') AS genres,"
            " COALESCE(array_agg(DISTINCT w.id) FILTER (WHERE w.id IS NOT NULL), '{}') AS work_ids,"
            " COALESCE(array_agg(DISTINCT wp.person_id) FILTER (WHERE wp.person_id IS NOT NULL), '{}') AS person_ids,"
            f" count(DISTINCT w.id) AS work_count, {sim} AS similarity"
            " FROM location l"
            " LEFT JOIN shooting s ON s.location_id = l.id"
            " LEFT JOIN work w ON w.id = s.work_id AND NOT w.retired"
            " LEFT JOIN LATERAL unnest(w.genres) AS g ON true"
            " LEFT JOIN work_person wp ON wp.work_id = w.id"
            " WHERE NOT l.retired AND l.lat IS NOT NULL"
            " GROUP BY l.id ORDER BY l.id",
            {"vec": Vector(vec).to_text() if vec is not None else None},
        )
        return [build(CourseCandidate, r) for r in rows]

    async def many(self, ids: list[int]) -> list[Location]:
        rows = await self._run(
            f"SELECT {_LOCATION_COLS} FROM location WHERE id = ANY(%(ids)s) AND NOT retired", {"ids": ids}
        )
        by_id = {r["id"]: build(Location, r) for r in rows}
        return [by_id[i] for i in ids if i in by_id]

    async def shooting_sources(self, location_id: int) -> list[str]:
        rows = await self._run(
            "SELECT DISTINCT source_id FROM shooting WHERE location_id = %(id)s ORDER BY source_id", {"id": location_id}
        )
        return [r["source_id"] for r in rows]
