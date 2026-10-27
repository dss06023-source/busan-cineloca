"""동기화 단계(IngestStep). 수집·좌표 단계는 WP-05 어댑터에 맞춰 여기에 더한다."""

from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Protocol

from app.batch.job import SyncContext
from app.data.adapters.kmdb_csv import SOURCE_ID as KMDB_SOURCE
from app.data.adapters.kmdb_csv import KmdbMovie, stored_kmdb
from app.data.adapters.policy import PolicyGuard
from app.pipeline.match import WorkMatcher


class KmdbCatalog(Protocol):
    by_id: dict[str, KmdbMovie]

    def candidates(self, title: str, year: int | None = None, limit: int = 3) -> list[KmdbMovie]: ...


class MatchWorksStep:
    """작품마다 KMDb 후보를 찾아 BR-11로 판정한다. 자동 연결이면 kmdb_id와 저장본을 채우고,
    검수 범위면 match_candidate만 남겨 반영 때 검수 큐(review_item)로 보낸다."""

    name = "match_kmdb"

    def __init__(self, catalog: KmdbCatalog, policy: PolicyGuard,
                 reviewed: Callable[[], Awaitable[dict[str, str]]] | None = None,
                 matcher: WorkMatcher | None = None):  # fmt: skip
        self.catalog, self.policy, self.reviewed = catalog, policy, reviewed
        self.matcher = matcher or WorkMatcher()

    async def run(self, ctx: SyncContext) -> None:
        # 관리자가 검수로 연결한 작품은 다시 매칭하지 않고 그 ID로 저장본만 채운다
        reviewed = await self.reviewed() if self.reviewed else {}
        out = []
        for w in ctx.works:
            if kmdb_id := reviewed.get(w.ext_key) or w.kmdb_id:  # 검수 연결, 또는 출처가 이미 준 KMDb ID
                status, sc = (w.match_status, w.match_score) if w.match_status != "unmatched" else ("auto", 1.0)
                out.append(replace(w, kmdb_id=kmdb_id, kmdb=self._stored(kmdb_id), match_status=status, match_score=sc))
                continue
            r = self.matcher.decide(w.title, w.release_year, self.catalog.candidates(w.title, w.release_year))
            if r.status == "auto":
                w = replace(w, kmdb_id=r.kmdb_id, match_status="auto", match_score=r.score,
                            kmdb=self._stored(r.kmdb_id))  # fmt: skip
            else:
                w = replace(w, match_status="unmatched", match_score=r.score,
                            match_candidate=r.kmdb_id if r.status == "review" else None)  # fmt: skip
            out.append(w)
        ctx.works = out

    def _stored(self, kmdb_id: str | None) -> dict | None:
        # STORE일 때만 줄거리·키워드·링크를 싣는다(ID_ONLY면 kmdb_id만, TBD-01)
        m = self.catalog.by_id.get(kmdb_id) if kmdb_id else None
        return stored_kmdb(m) if m and self.policy.policies.get(KMDB_SOURCE) == "STORE" else None
