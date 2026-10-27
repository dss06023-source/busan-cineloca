"""UsageRepository(COMP-12): 공급자·외부 API 하루 호출 수(NFR-005). 날짜 기준은 부르는 쪽이 정한다."""

from datetime import date

from psycopg_pool import AsyncConnectionPool


class UsageRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def incr(self, day: date, key: str, by: int = 1) -> int:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO usage_counter(day, key, count) VALUES (%(d)s, %(k)s, %(n)s)"
                " ON CONFLICT (day, key) DO UPDATE SET count = usage_counter.count + EXCLUDED.count"
                " RETURNING count",
                {"d": day, "k": key, "n": by},
            )
            return (await cur.fetchone())["count"]

    async def get(self, day: date, key: str) -> int:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT count FROM usage_counter WHERE day = %(d)s AND key = %(k)s", {"d": day, "k": key}
            )
            row = await cur.fetchone()
        return row["count"] if row else 0
