"""SourceRepository(COMP-12): 출처 대장(source 테이블)."""

from psycopg_pool import AsyncConnectionPool

from app.data.models import Source
from app.data.repositories._rows import build

_COLS = "id, org, name, url, license, policy, base_date"


class SourceRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def all(self) -> list[Source]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM source ORDER BY id")
            return [build(Source, r) for r in await cur.fetchall()]

    async def get_many(self, ids: list[str]) -> list[Source]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(f"SELECT {_COLS} FROM source WHERE id = ANY(%(ids)s) ORDER BY id", {"ids": ids})
            return [build(Source, r) for r in await cur.fetchall()]
