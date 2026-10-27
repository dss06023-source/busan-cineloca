"""API-025 상태 확인용 조회."""

from datetime import date

from psycopg_pool import AsyncConnectionPool


async def ping(pool: AsyncConnectionPool) -> bool:
    async with pool.connection() as conn:
        await conn.execute("SELECT 1")
    return True


async def usage_for(pool: AsyncConnectionPool, day: date, prefix: str) -> dict[str, int]:
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT key, count FROM usage_counter WHERE day = %(day)s AND key LIKE %(prefix)s",
            {"day": day, "prefix": prefix + "%"},
        )
        rows = await cur.fetchall()
    return {r["key"]: r["count"] for r in rows}
