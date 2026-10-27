"""QueryService(COMP-06): AI 대화형 탐색(API-013), 필터 패널 검색(API-014), 새 대화(API-015)."""

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from app.data.ai_gateway.deadline import Deadline
from app.data.models import Point
from app.pipeline.query.context import Criteria, QueryContext, QueryStatus
from app.pipeline.query.steps import ConditionRelaxer, QueryPipeline, TemplateSearcher

AI_SOURCE = "DATA-11"
STATION_SOURCE = "DATA-08"


class SessionStore:
    """세션 ID별 최근 3턴 조건을 서버 메모리에 30분 둔다(FR-408, ADR-013). 워커가 1개라 메모리로 충분하다."""

    MAX_TURNS = 3
    TTL_S = 30 * 60
    MAX_SESSIONS = 10_000

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._data: OrderedDict[str, tuple[float, list[dict], Criteria | None]] = OrderedDict()

    def _live(self, session_id: str):
        item = self._data.get(session_id)
        if item and self.clock() - item[0] > self.TTL_S:
            del self._data[session_id]
            return None
        return item

    def get(self, session_id: str) -> list[dict]:
        item = self._live(session_id)
        return list(item[1]) if item else []

    def last_criteria(self, session_id: str) -> Criteria | None:
        item = self._live(session_id)
        return item[2] if item else None

    def append(self, session_id: str, raw: dict, criteria: Criteria) -> None:
        turns = [*self.get(session_id), raw][-self.MAX_TURNS :]
        self._data[session_id] = (self.clock(), turns, criteria)
        self._data.move_to_end(session_id)
        while len(self._data) > self.MAX_SESSIONS:
            self._data.popitem(last=False)

    def clear(self, session_id: str) -> None:
        self._data.pop(session_id, None)


@dataclass
class QueryResult:
    status: QueryStatus
    ctx: QueryContext
    prefill: Criteria | None
    source_ids: list[str]


def _sources(ctx: QueryContext) -> list[str]:
    s = {sid for r in ctx.results for sid in r.source_ids}
    if any(getattr(r, "nearest_station_id", None) for r in ctx.results) or ctx.criteria.base_kind in (
        "station",
        "any_station",
    ):
        s.add(STATION_SOURCE)
    if ctx.summary:
        s.add(AI_SOURCE)
    return sorted(s)


class QueryService:
    def __init__(
        self,
        pipeline: QueryPipeline,
        searcher: TemplateSearcher,
        sessions: SessionStore,
        deadline_s: float,
        works_by_locations,
    ):
        self.pipeline = pipeline
        self.searcher = searcher
        self.relaxer = ConditionRelaxer(searcher)
        self.sessions = sessions
        self.deadline_s = deadline_s
        self.works_by_locations = works_by_locations  # 결과 카드의 작품(최신작 먼저)

    async def ask(self, session_id: str, text: str, here: Point | None = None) -> QueryResult:
        ctx = QueryContext(
            text=text, here=here, history=self.sessions.get(session_id), deadline=Deadline(self.deadline_s)
        )
        ctx = await self.pipeline.run(ctx)
        if ctx.status in (QueryStatus.OK, QueryStatus.RELAXED, QueryStatus.NOT_FOUND):
            self.sessions.append(session_id, ctx.raw, ctx.criteria)
        prefill = None
        if ctx.status == QueryStatus.FALLBACK:
            # 추출에 실패했으므로 직전 대화의 조건만 미리 채운다(FR-411)
            prefill = self.sessions.last_criteria(session_id)
        elif ctx.status in (QueryStatus.NOT_FOUND, QueryStatus.NEEDS_CHOICE):
            prefill = ctx.criteria
        return QueryResult(ctx.status, ctx, prefill, _sources(ctx))

    async def search(self, criteria: Criteria, labels: dict[str, str] | None = None) -> QueryResult:
        """필터 패널(API-014): «5»·«6»만, AI 없이 같은 템플릿(FR-410). labels는 칩 문구용."""
        ctx = QueryContext(text="", criteria=criteria, labels=labels or {})
        ctx = await self.searcher.apply(ctx)
        ctx = await self.relaxer.apply(ctx)
        return QueryResult(ctx.status, ctx, None, _sources(ctx))

    def reset(self, session_id: str) -> None:
        self.sessions.clear(session_id)
