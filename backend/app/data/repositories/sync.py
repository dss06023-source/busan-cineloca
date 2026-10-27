"""SyncRepository(COMP-12): 동기화 요청과 실행 기록(sync_run, API-021, ADR-012)."""

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.data.models import SyncRun
from app.data.repositories._rows import build

_COLS = "id, trigger, status, requested_by, counts, prev_counts, failures"


class SyncRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def request(self, by: str, trigger: str = "manual") -> int:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO sync_run(trigger, status, requested_by) VALUES (%(t)s, 'requested', %(by)s) RETURNING id",
                {"t": trigger, "by": by},
            )
            return (await cur.fetchone())["id"]

    async def next_requested(self) -> SyncRun | None:
        """가장 오래된 요청 하나를 running으로 바꿔 가져온다. 배치 두 개가 같은 요청을 잡지 않는다."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE sync_run SET status = 'running', started_at = now() WHERE id = ("
                " SELECT id FROM sync_run WHERE status = 'requested' ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)"
                f" RETURNING {_COLS}"
            )
            row = await cur.fetchone()
        return build(SyncRun, row) if row else None

    async def save(self, run: SyncRun) -> None:
        """실행 결과를 남긴다. 끝난 상태(published·rejected·failed)면 끝난 시각도 적는다."""
        async with self.pool.connection() as conn:
            await conn.execute(
                "UPDATE sync_run SET status = %(status)s::text, counts = %(counts)s, prev_counts = %(prev)s,"
                " failures = %(failures)s,"
                " finished_at = CASE WHEN %(status)s::text IN ('published','rejected','failed') THEN now() END"
                " WHERE id = %(id)s",
                {
                    "id": run.id,
                    "status": run.status,
                    "counts": Jsonb(run.counts) if run.counts is not None else None,
                    "prev": Jsonb(run.prev_counts) if run.prev_counts is not None else None,
                    "failures": Jsonb(run.failures) if run.failures is not None else None,
                },
            )

    async def recent(self, limit: int = 10) -> list[SyncRun]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM sync_run ORDER BY id DESC LIMIT %(n)s", {"n": min(max(limit, 1), 50)}
            )
            return [build(SyncRun, r) for r in await cur.fetchall()]
