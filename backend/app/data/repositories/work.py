"""WorkRepository(COMP-12): 작품 목록·상세(API-001·002)."""

from psycopg_pool import AsyncConnectionPool

from app.data.models import Page, Person, Work, WorkBrief, WorkDetail, WorkLocation, WorkQuery
from app.data.repositories._rows import build
from app.data.text import normalize

PAGE_SIZE = 20
MAX_PEOPLE = 5
_ORDER = {  # 허용 목록(ADR-010)
    "locations": "location_count DESC, w.release_year DESC NULLS LAST, w.id",
    "year": "w.release_year DESC NULLS LAST, w.id",
}
_COUNT = (
    "(SELECT count(DISTINCT s.location_id) FROM shooting s JOIN location l ON l.id = s.location_id"
    " WHERE s.work_id = w.id AND NOT l.retired)"
)
_COLS = f"w.id, w.title, w.release_year, w.genres, w.source_id, w.kmdb_id, w.kobis_movie_cd, {_COUNT} AS location_count"
_WHERE = (
    "NOT w.retired"
    " AND (%(q)s::text IS NULL OR w.title_norm LIKE '%%' || %(q)s || '%%')"
    " AND (%(genre)s::text IS NULL OR %(genre)s = ANY(w.genres))"
)


class WorkRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def page(self, query: WorkQuery) -> Page:
        if query.sort not in _ORDER or query.page < 1:
            raise ValueError("sort는 year·locations, page는 1 이상")
        params = {
            "q": normalize(query.q) or None if query.q else None,
            "genre": query.genre,
            "limit": PAGE_SIZE,
            "offset": (query.page - 1) * PAGE_SIZE,
        }
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM work w WHERE {_WHERE} ORDER BY {_ORDER[query.sort]}"
                " LIMIT %(limit)s OFFSET %(offset)s",
                params,
            )
            items = [build(Work, r) for r in await cur.fetchall()]
            cur = await conn.execute(f"SELECT count(*) AS n FROM work w WHERE {_WHERE}", params)
            total = (await cur.fetchone())["n"]
        return Page(items=items, total=total)

    async def get(self, work_id: int) -> WorkDetail | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS}, w.kmdb FROM work w WHERE w.id = %(id)s AND NOT w.retired", {"id": work_id}
            )
            row = await cur.fetchone()
            if row is None:
                return None
            cur = await conn.execute(
                "SELECT p.id, p.name, wp.role, wp.ord FROM work_person wp JOIN person p ON p.id = wp.person_id"
                " WHERE wp.work_id = %(id)s ORDER BY wp.role = 'actor', wp.ord LIMIT %(n)s",
                {"id": work_id, "n": MAX_PEOPLE},
            )
            people = [build(Person, r) for r in await cur.fetchall()]
            cur = await conn.execute(
                "SELECT l.id, l.name, l.gu, l.lat, l.lon, s.source_id FROM shooting s"
                " JOIN location l ON l.id = s.location_id"
                " WHERE s.work_id = %(id)s AND NOT l.retired ORDER BY l.id, s.source_id",
                {"id": work_id},
            )
            locations = [build(WorkLocation, r) for r in await cur.fetchall()]
        kmdb = row.pop("kmdb")
        work = build(Work, row)
        source_ids = list(dict.fromkeys([work.source_id, *(loc.source_id for loc in locations)]))
        return WorkDetail(work=work, people=people, locations=locations, source_ids=source_ids, kmdb=kmdb)

    async def related(self, work_id: int, n: int = 5) -> list[WorkBrief]:
        """같은 촬영지나 같은 인물을 공유하는 작품, 공유 수 순(FR-802)."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "WITH shared AS ("
                " SELECT s2.work_id AS id FROM shooting s1 JOIN shooting s2 ON s2.location_id = s1.location_id"
                " WHERE s1.work_id = %(id)s AND s2.work_id <> %(id)s"
                " UNION ALL"
                " SELECT p2.work_id FROM work_person p1 JOIN work_person p2 ON p2.person_id = p1.person_id"
                " WHERE p1.work_id = %(id)s AND p2.work_id <> %(id)s)"
                " SELECT w.id, w.title, w.release_year FROM shared JOIN work w ON w.id = shared.id"
                " WHERE NOT w.retired GROUP BY w.id ORDER BY count(*) DESC, w.release_year DESC NULLS LAST, w.id"
                " LIMIT %(n)s",
                {"id": work_id, "n": n},
            )
            return [build(WorkBrief, r) for r in await cur.fetchall()]

    async def by_locations(self, location_ids: list[int]) -> dict[int, list[WorkBrief]]:
        """촬영지마다 촬영된 작품(최신작 먼저). 요약 카드는 앞의 3편만 쓴다(FR-206)."""
        result: dict[int, list[WorkBrief]] = {i: [] for i in location_ids}
        if not location_ids:
            return result
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT DISTINCT s.location_id, w.id, w.title, w.release_year FROM shooting s"
                " JOIN work w ON w.id = s.work_id WHERE s.location_id = ANY(%(ids)s) AND NOT w.retired"
                " ORDER BY s.location_id, w.release_year DESC NULLS LAST, w.id",
                {"ids": location_ids},
            )
            for r in await cur.fetchall():
                result[r["location_id"]].append(build(WorkBrief, r))
        return result

    async def set_match(self, work_id: int, kmdb_id: str) -> bool:
        """검수에서 승인한 KMDb 연결(BR-11). 다른 작품이 쓰는 kmdb_id면 UniqueViolation.
        연결이 바뀌면 이전 저장본(kmdb)은 비우고, 다음 동기화가 새 ID로 채운다."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE work SET kmdb = CASE WHEN kmdb_id = %(k)s THEN kmdb END, kmdb_id = %(k)s,"
                " match_status = 'reviewed' WHERE id = %(id)s RETURNING id",
                {"id": work_id, "k": kmdb_id},
            )
            return await cur.fetchone() is not None

    async def reviewed_matches(self) -> dict[str, str]:
        """관리자가 검수로 연결한 작품의 ext_key → kmdb_id. 동기화가 이 연결로 저장본을 채운다."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT ext_key, kmdb_id FROM work WHERE match_status = 'reviewed' AND kmdb_id IS NOT NULL"
            )
            return {r["ext_key"]: r["kmdb_id"] for r in await cur.fetchall()}

    async def person_name(self, person_id: int) -> str | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute("SELECT name FROM person WHERE id = %(id)s", {"id": person_id})
            row = await cur.fetchone()
        return row["name"] if row else None

    async def genres(self) -> list[str]:
        async with self.pool.connection() as conn:
            cur = await conn.execute("SELECT DISTINCT unnest(genres) AS g FROM work WHERE NOT retired ORDER BY g")
            return [r["g"] for r in await cur.fetchall()]

    async def year_range(self) -> tuple[int, int] | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT min(release_year) AS lo, max(release_year) AS hi FROM work WHERE NOT retired"
            )
            row = await cur.fetchone()
        return (row["lo"], row["hi"]) if row["lo"] is not None else None
