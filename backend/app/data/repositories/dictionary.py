"""DictionaryRepository(COMP-12): 작품·인물·구·역·태그 이름 사전 대조(FR-403, DictionaryResolver가 씀)."""

from pgvector import Vector
from psycopg_pool import AsyncConnectionPool

from app.data.models import DictHit
from app.data.repositories._rows import build
from app.data.text import normalize

KINDS = ("work", "person", "gu", "station", "tag")


class DictionaryRepository:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def fuzzy(self, kind: str, text: str, k: int = 3) -> list[DictHit]:
        """트라이그램 유사도 순 상위 k개. 점수 기준(0.35)은 부르는 쪽이 정한다."""
        if kind not in KINDS:
            raise ValueError(kind)
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT kind, surface, canonical_id, similarity(surface, %(q)s) AS score FROM dict_entry"
                " WHERE kind = %(kind)s ORDER BY score DESC, id LIMIT %(k)s",
                {"kind": kind, "q": normalize(text), "k": k},
            )
            return [build(DictHit, r) for r in await cur.fetchall()]

    async def semantic(self, kind: str, vec: list[float], k: int = 3) -> list[DictHit]:
        """코사인 유사도(1 − 거리) 순 상위 k개. 벡터가 없는 항목은 빠진다."""
        if kind not in KINDS:
            raise ValueError(kind)
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT kind, surface, canonical_id, 1 - (embedding <=> %(vec)s::vector) AS score FROM dict_entry"
                " WHERE kind = %(kind)s AND embedding IS NOT NULL"
                " ORDER BY embedding <=> %(vec)s::vector, id LIMIT %(k)s",
                {"kind": kind, "vec": Vector(vec).to_text(), "k": k},
            )
            return [build(DictHit, r) for r in await cur.fetchall()]

    async def lexicon(self) -> list[str]:
        """근거 대조(EntityLexicon)에 쓸 지식베이스의 작품·인물·장소·구·군 이름."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT title AS name FROM work WHERE NOT retired"
                " UNION SELECT name FROM person"
                " UNION SELECT name FROM location WHERE NOT retired"
                " UNION SELECT gu FROM location WHERE gu IS NOT NULL"
            )
            return [r["name"] for r in await cur.fetchall()]
