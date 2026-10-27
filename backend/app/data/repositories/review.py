"""ReviewRepository(COMP-12): 태그·매칭 검수 큐(API-022, BR-04·11)."""

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.data.models import ReviewItem
from app.data.repositories._rows import build

_COLS = "id, kind, target_type, target_id, proposal, proposer, model, score, status"


class ReviewRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def add(
        self,
        kind: str,
        target_type: str,
        target_id: int,
        proposal: dict | None,
        proposer: str | None,
        model: str | None = None,
        score: float | None = None,
    ) -> int:
        """제안은 언제나 'pending'으로만 들어간다(BR-04)."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "INSERT INTO review_item(kind, target_type, target_id, proposal, proposer, model, score)"
                " VALUES (%(kind)s, %(tt)s, %(tid)s, %(proposal)s, %(proposer)s, %(model)s, %(score)s) RETURNING id",
                {
                    "kind": kind,
                    "tt": target_type,
                    "tid": target_id,
                    "proposal": Jsonb(proposal) if proposal is not None else None,
                    "proposer": proposer,
                    "model": model,
                    "score": score,
                },
            )
            return (await cur.fetchone())["id"]

    async def pending(self, kind: str | None = None) -> list[ReviewItem]:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                f"SELECT {_COLS} FROM review_item WHERE status = 'pending'"
                " AND (%(kind)s::text IS NULL OR kind = %(kind)s) ORDER BY created_at, id",
                {"kind": kind},
            )
            return [build(ReviewItem, r) for r in await cur.fetchall()]

    async def decide(self, item_id: int, status: str, by: str) -> ReviewItem | None:
        """pending 항목만 처리한다. 이미 처리했거나 없으면 None."""
        if status not in ("approved", "rejected"):
            raise ValueError(status)
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE review_item SET status = %(status)s, handled_by = %(by)s, handled_at = now()"
                f" WHERE id = %(id)s AND status = 'pending' RETURNING {_COLS}",
                {"id": item_id, "status": status, "by": by},
            )
            row = await cur.fetchone()
        return build(ReviewItem, row) if row else None
