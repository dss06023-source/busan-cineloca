"""F4 파이프라인 단계 단위 테스트: ConditionRelaxer 순서, ContextMerger, SessionStore, 칩, 파이프라인 중단."""

from app.data.models import DictHit, Point
from app.pipeline.query.context import Criteria, QueryContext, QueryStatus
from app.pipeline.query.steps import ConditionRelaxer, ContextMerger, DictionaryResolver, QueryPipeline, chips_for
from app.services.query.service import SessionStore

FULL = Criteria(
    person_ids=[1], genres=["액션"], gus=["중구"], year_from=2000, year_to=2010,
    base_kind="any_station", travel_mode="walk", travel_min=10,
)  # fmt: skip


class Searcher:
    """found_after번째 완화부터 결과가 나오는 가짜 검색기."""

    def __init__(self, found_after: int):
        self.found_after = found_after
        self.calls: list[Criteria] = []

    async def search(self, c):
        self.calls.append(c)
        return ["hit"] if len(self.calls) >= self.found_after else []


async def relax(found_after):
    s = Searcher(found_after)
    ctx = await ConditionRelaxer(s).apply(QueryContext(text="", criteria=FULL))
    return ctx, s


async def test_relax_order_travel_years_genres_gus():
    for n, expected in enumerate([["travel"], ["travel", "years"], ["travel", "years", "genres"]], start=1):
        ctx, _ = await relax(n)
        assert ctx.relaxed == expected and ctx.status == QueryStatus.RELAXED
    ctx, s = await relax(99)
    assert ctx.relaxed == ["travel", "years", "genres", "gus"] and ctx.status == QueryStatus.NOT_FOUND
    assert s.calls[-1] == Criteria(person_ids=[1])  # 작품·인물은 풀지 않는다


async def test_relax_skips_absent_conditions_and_keeps_results():
    s = Searcher(1)
    ctx = await ConditionRelaxer(s).apply(QueryContext(text="", criteria=Criteria(gus=["중구"])))
    assert ctx.relaxed == ["gus"]
    done = QueryContext(text="", results=["x"])
    assert (await ConditionRelaxer(s).apply(done)).relaxed == []


async def test_context_merger_overrides_only_given_fields():
    ctx = QueryContext(text="", history=[{"persons": ["강도윤"], "districts": ["동구"]}], raw={"districts": ["중구"]})
    out = await ContextMerger().apply(ctx)
    assert out.raw == {"persons": ["강도윤"], "districts": ["중구"]}


def test_session_store_turns_and_ttl():
    t = [0.0]
    s = SessionStore(clock=lambda: t[0])
    for i in range(5):
        s.append("a", {"i": i}, Criteria())
    assert s.get("a") == [{"i": 2}, {"i": 3}, {"i": 4}]
    t[0] = 30 * 60 + 1
    assert s.get("a") == [] and s.last_criteria("a") is None
    s.append("b", {}, Criteria(gus=["중구"]))
    s.clear("b")
    assert s.get("b") == []


def test_chips_and_without():
    labels = {"person_ids:1": "강도윤"}
    chips = {c.field: c.label for c in chips_for(FULL, labels)}
    assert chips == {
        "person_ids": "강도윤",
        "genres": "액션",
        "gus": "중구",
        "years": "2000~2010년",
        "travel": "지하철역에서 걸어서 10분",
    }
    assert FULL.without("travel").base_kind is None and FULL.without("years").year_from is None
    near = Criteria(base_kind="point", point=Point(35.1, 129.0))
    assert chips_for(near, {})[0].label == "현재 위치에서 반경 1km"


async def test_pipeline_stops_on_status():
    seen = []

    class Step:
        def __init__(self, name, status=None):
            self.name, self.status = name, status

        async def apply(self, ctx):
            seen.append(self.name)
            if self.status:
                ctx.status = self.status
            return ctx

    await QueryPipeline([Step("a"), Step("b", QueryStatus.FALLBACK), Step("c")]).run(QueryContext(text=""))
    assert seen == ["a", "b"]


class Dict:
    def __init__(self, hits):
        self.hits = hits

    async def fuzzy(self, kind, text, k=3):
        return self.hits

    async def semantic(self, kind, vec, k=3):
        return []


async def allowed():
    return {"genres": ["액션"], "districts": ["중구"]}


async def resolve(hits, raw, here=None):
    r = DictionaryResolver(Dict(hits), None, None, allowed, lambda i: _title(i))
    return await r.apply(QueryContext(text="", raw=raw, here=here))


async def _title(i):
    return f"작품{i}"


async def test_resolver_choice_when_ambiguous():
    hits = [DictHit("person", "김민수", "1", 0.7), DictHit("person", "김민서", "2", 0.65)]
    ctx = await resolve(hits, {"persons": ["김민"], "result_type": "LOCATION"})
    assert ctx.status == QueryStatus.NEEDS_CHOICE and [c.value for c in ctx.choices] == ["1", "2"]


async def test_resolver_exact_and_current_location():
    hits = [DictHit("work", "가상", "3", 1.0), DictHit("work", "가상2", "4", 0.9)]
    ctx = await resolve(
        hits, {"works": ["가상"], "base": {"kind": "current"}, "travel": {"mode": "walk", "minutes": 5}}
    )
    assert ctx.criteria.work_ids == [3] and ctx.labels == {"work_ids:3": "작품3"}
    assert ctx.criteria.base_kind is None and ctx.notices  # 현재 위치를 모르면 뺀다
    ctx = await resolve([], {"base": {"kind": "current"}}, here=Point(35.1, 129.0))
    assert ctx.criteria.base_kind == "point" and ctx.criteria.point == Point(35.1, 129.0)
