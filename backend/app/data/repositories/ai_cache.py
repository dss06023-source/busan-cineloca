"""AICacheRepository(COMP-12): 검증을 통과한 AI 응답 캐시(AI-REQ-15). 키는 게이트웨이가 만든 SHA-256."""

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool


class AICacheRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def get(self, key: str) -> dict | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT response FROM ai_cache WHERE key = %(k)s AND expires_at > now()", {"k": key}
            )
            row = await cur.fetchone()
        return row["response"] if row else None

    async def put(self, key: str, task: str, value: dict, ttl_h: int = 24) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO ai_cache(key, task, response, expires_at)"
                " VALUES (%(k)s, %(task)s, %(v)s, now() + make_interval(hours => %(ttl)s))"
                " ON CONFLICT (key) DO UPDATE SET response = EXCLUDED.response, created_at = now(),"
                " expires_at = EXCLUDED.expires_at",
                {"k": key, "task": task, "v": Jsonb(value), "ttl": ttl_h},
            )

    async def purge_expired(self) -> int:
        async with self.pool.connection() as conn:
            cur = await conn.execute("DELETE FROM ai_cache WHERE expires_at <= now()")
            return cur.rowcount
