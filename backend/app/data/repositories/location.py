"""LocationRepository(COMP-12): 근접·조건 검색, 촬영지 조회, 관리자 속성 편집."""

from dataclasses import replace

from psycopg_pool import AsyncConnectionPool

from app.data.models import Conditions, Location, LocationAttrs, LocationHit, Photo, Point, WorkHit
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

    async def shooting_sources(self, location_id: int) -> list[str]:
        rows = await self._run(
            "SELECT DISTINCT source_id FROM shooting WHERE location_id = %(id)s ORDER BY source_id", {"id": location_id}
        )
        return [r["source_id"] for r in rows]
