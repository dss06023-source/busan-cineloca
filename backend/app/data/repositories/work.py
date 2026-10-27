"""WorkRepository(COMP-12): 작품 목록·상세(API-001·002)."""

from psycopg_pool import AsyncConnectionPool

from app.data.models import Page, Person, Work, WorkDetail, WorkLocation, WorkQuery
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
                f"SELECT {_COLS} FROM work w WHERE w.id = %(id)s AND NOT w.retired", {"id": work_id}
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
        work = build(Work, row)
        source_ids = list(dict.fromkeys([work.source_id, *(loc.source_id for loc in locations)]))
        return WorkDetail(work=work, people=people, locations=locations, source_ids=source_ids)
