"""F4 파이프라인 단계 9개(SDD CD-03). «1»~«9» 순서는 QueryPipeline이 정한다."""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Protocol

from app.data.ai_gateway.errors import AIUnavailable, ProviderError
from app.data.ai_gateway.gateway import LLMClient
from app.data.models import Conditions, DictHit, LocationHit, Point, WorkBrief
from app.data.repositories.dictionary import DictionaryRepository
from app.data.repositories.location import LocationRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.templates import walk_radius_m
from app.data.text import normalize
from app.pipeline.query.context import STOP, Chip, Choice, Criteria, QueryContext, QueryStatus
from app.support.grounding import EntityLexicon, GroundingVerifier, PhraseFilter
from app.support.privacy import mask

log = logging.getLogger(__name__)

DEFAULT_RADIUS_M = 1000  # 기준 위치만 있고 이동 조건이 없을 때
SURE = 0.5  # 트라이그램 점수: 이 이상이면 후보로 본다
GAP = 0.15  # 1등과 2등 차이가 이 이상이면 1등으로 확정
SEMANTIC_SURE = 0.85
GENERIC_STATIONS = {"", "역", "지하철", "지하철역", "도시철도", "도시철도역", "전철역", "아무역"}
SUMMARY_TOP = 10  # FR-407: 상위 10건만 근거로
SUMMARY_MAX = 3


class QueryStep(Protocol):
    async def apply(self, ctx: QueryContext) -> QueryContext: ...


class SessionView(Protocol):
    def get(self, session_id: str) -> list[dict]: ...


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class MaskStep:
    """«1» 개인정보를 가린다(FR-702). 가린 원문은 이후 단계와 로그에 남지 않는다."""

    async def apply(self, ctx: QueryContext) -> QueryContext:
        ctx.masked, ctx.masked_kinds = mask(ctx.text)
        ctx.text = ""
        return ctx


class ConditionExtractor:
    """«2» extract_query로 conditions.v1을 받는다. 실패하면 FALLBACK(FR-411), 범위 밖이면 OUT_OF_SCOPE(FR-409)."""

    def __init__(self, llm: LLMClient, allowed: Callable[[], Awaitable[dict]]):
        self.llm = llm
        self.allowed = allowed

    async def apply(self, ctx: QueryContext) -> QueryContext:
        inputs = {"allowed": await self.allowed(), "user_input": ctx.masked}
        try:
            result = await self.llm.generate("extract_query", inputs, ctx.deadline)
        except AIUnavailable as e:
            log.info("extract_query unavailable", extra={"reasons": e.reasons})
            ctx.status = QueryStatus.FALLBACK
            return ctx
        ctx.raw = result.data
        if ctx.raw.get("out_of_scope"):
            ctx.status = QueryStatus.OUT_OF_SCOPE
        return ctx


class ContextMerger:
    """«3» 직전 조건에 이번 조건을 덮어쓴다(FR-408). 이번에 말하지 않은 조건은 직전 값을 유지한다."""

    async def apply(self, ctx: QueryContext) -> QueryContext:
        if not ctx.history:
            return ctx
        merged = dict(ctx.history[-1])
        merged.update({k: v for k, v in ctx.raw.items() if v not in (None, [], {}, "")})
        ctx.raw = merged
        return ctx


class DictionaryResolver:
    """«4» 이름을 사전의 표준 ID로 바꾼다(FR-403). 후보가 여럿이면 NEEDS_CHOICE, 없으면 빼고 알린다."""

    def __init__(
        self,
        dictionary: DictionaryRepository,
        locations: LocationRepository,
        stations: StationRepository,
        allowed: Callable[[], Awaitable[dict]],
        work_title: Callable[[int], Awaitable[str | None]],
        embedder: Embedder | None = None,
    ):
        self.dictionary = dictionary
        self.locations = locations
        self.stations = stations
        self.allowed = allowed
        self.work_title = work_title
        self.embedder = embedder

    async def _lookup(self, kind: str, name: str, ctx: QueryContext, field: str) -> DictHit | None:
        hits = await self.dictionary.fuzzy(kind, name)
        good = [h for h in hits if h.score >= SURE]
        if good and (good[0].score >= 0.999 or len(good) == 1 or good[0].score - good[1].score >= GAP):
            return good[0]
        if len(good) >= 2:
            ctx.choices += [Choice(field, name, h.surface, h.canonical_id) for h in good]
            return None
        if self.embedder is not None:
            try:
                vec = (await self.embedder.embed([name]))[0]
                sem = await self.dictionary.semantic(kind, vec, 1)
                if sem and sem[0].score >= SEMANTIC_SURE:
                    return sem[0]
            except ProviderError:
                pass  # 임베딩이 안 되면 트라이그램만(build-plan 6장)
        ctx.notices.append(f"'{name}'을(를) 찾지 못해 조건에서 뺐습니다.")
        return None

    async def apply(self, ctx: QueryContext) -> QueryContext:
        raw, allowed = ctx.raw, await self.allowed()
        c = Criteria(result_type=raw.get("result_type", "LOCATION"))
        labels: dict[str, str] = {}

        async def ids(field: str, kind: str, names: list[str]) -> list[int] | None:
            out = []
            for name in names[:3]:
                hit = await self._lookup(kind, name, ctx, field)
                if hit:
                    out.append(int(hit.canonical_id))
                    labels[f"{field}:{hit.canonical_id}"] = (
                        await self.work_title(int(hit.canonical_id)) if kind == "work" else hit.surface
                    ) or name
            return list(dict.fromkeys(out)) or None

        c = replace(c, work_ids=await ids("work_ids", "work", raw.get("works") or []))
        c = replace(c, person_ids=await ids("person_ids", "person", raw.get("persons") or []))
        c = replace(c, genres=self._allowed(raw.get("genres"), allowed["genres"], ctx))
        gus = []
        for g in raw.get("districts") or []:
            if g in allowed["districts"]:
                gus.append(g)
            elif hit := await self._lookup("gu", g, ctx, "gus"):
                gus.append(hit.canonical_id)
        c = replace(c, gus=list(dict.fromkeys(gus)) or None)
        years = raw.get("years") or {}
        c = replace(c, year_from=years.get("from"), year_to=years.get("to"))
        c = await self._base(c, raw.get("base"), raw.get("travel"), ctx, labels)
        ctx.criteria, ctx.labels = c, labels
        if ctx.choices:
            ctx.status = QueryStatus.NEEDS_CHOICE
        return ctx

    @staticmethod
    def _allowed(values: list[str] | None, allowed: list[str], ctx: QueryContext) -> list[str] | None:
        ok = [v for v in values or [] if v in allowed]
        for v in values or []:
            if v not in allowed:
                ctx.notices.append(f"'{v}'은(는) 고를 수 있는 값이 아니라 뺐습니다.")
        return ok or None

    async def _base(self, c: Criteria, base: dict | None, travel: dict | None, ctx: QueryContext, labels) -> Criteria:
        mode = (travel or {}).get("mode")
        minutes = (travel or {}).get("minutes")
        c = replace(c, travel_mode=mode, travel_min=minutes) if mode and minutes else c
        kind = (base or {}).get("kind")
        name = ((base or {}).get("name") or "").strip()
        if kind is None:
            if c.travel_mode == "walk":
                return replace(c, base_kind="any_station")  # '걸어서 N분'만 말하면 아무 역에서
            if c.travel_mode:
                ctx.notices.append("기준 위치가 없어 이동 조건을 뺐습니다.")
            return replace(c, travel_mode=None, travel_min=None)
        if kind == "current":
            if ctx.here is None:
                ctx.notices.append("현재 위치를 알 수 없어 위치 조건을 뺐습니다.")
                return replace(c, travel_mode=None, travel_min=None)
            return replace(c, base_kind="point", point=ctx.here)
        if kind == "station":
            key = normalize(name)
            if key.removesuffix("역") in GENERIC_STATIONS or key in GENERIC_STATIONS:
                return replace(c, base_kind="any_station", travel_mode="walk", travel_min=c.travel_min or 10)
            hit = await self._lookup("station", key if key.endswith("역") else key + "역", ctx, "travel")
            if hit is None:
                return replace(c, travel_mode=None, travel_min=None)
            labels[f"station:{hit.canonical_id}"] = hit.surface.removesuffix("역")
            return replace(c, base_kind="station", station_id=hit.canonical_id)
        hits = [h for h in await self.locations.by_name(name) if h.score >= SURE]
        if not hits:
            ctx.notices.append(f"'{name}'을(를) 찾지 못해 위치 조건을 뺐습니다.")
            return replace(c, travel_mode=None, travel_min=None)
        labels[f"location:{hits[0].canonical_id}"] = hits[0].surface
        return replace(c, base_kind="location", location_id=int(hits[0].canonical_id))


def chips_for(c: Criteria, labels: dict[str, str]) -> list[Chip]:
    """해석 조건 칩(FR-412)."""
    out = []
    for field in ("work_ids", "person_ids"):
        if getattr(c, field):
            out.append(Chip(field, ", ".join(labels.get(f"{field}:{i}", str(i)) for i in getattr(c, field))))
    if c.genres:
        out.append(Chip("genres", "·".join(c.genres)))
    if c.gus:
        out.append(Chip("gus", "·".join(c.gus)))
    if c.year_from or c.year_to:
        out.append(Chip("years", f"{c.year_from or ''}~{c.year_to or ''}년"))
    if c.base_kind:
        where = {
            "any_station": "지하철역",
            "station": f"{labels.get(f'station:{c.station_id}', c.station_id)}역",
            "location": labels.get(f"location:{c.location_id}", "장소"),
            "point": "현재 위치",
        }[c.base_kind]
        how = {"walk": f"걸어서 {c.travel_min}분", "subway": f"도시철도로 {c.travel_min}분"}.get(
            c.travel_mode or "", f"반경 {DEFAULT_RADIUS_M // 1000}km"
        )
        out.append(Chip("travel", f"{where}에서 {how}"))
    return out


class TemplateSearcher:
    """«5» Criteria를 템플릿 매개변수(Conditions)로 바꿔 검색한다(FR-404). 필터 패널도 이 단계부터 쓴다."""

    def __init__(self, locations: LocationRepository, stations: StationRepository):
        self.locations = locations
        self.stations = stations

    async def conditions(self, c: Criteria) -> Conditions:
        base = Conditions(
            work_ids=c.work_ids, person_ids=c.person_ids, genres=c.genres, gus=c.gus,
            year_from=c.year_from, year_to=c.year_to, result_type=c.result_type,
        )  # fmt: skip
        minutes = c.travel_min
        if c.base_kind == "any_station":
            return replace(base, any_station_walk_min=minutes or 10)
        if c.base_kind == "station" and c.travel_mode == "subway":
            return replace(base, from_station=c.station_id, minutes=minutes)
        point = None
        if c.base_kind == "station":
            s = await self.stations.get(c.station_id)
            point = Point(s.lat, s.lon) if s else None
        elif c.base_kind == "location":
            loc = await self.locations.get(c.location_id)
            point = Point(loc.lat, loc.lon) if loc and loc.lat is not None else None
        elif c.base_kind == "point":
            point = c.point
        if point is None:
            return base
        radius = walk_radius_m(minutes) if c.travel_mode == "walk" and minutes else DEFAULT_RADIUS_M
        return replace(base, point=point, radius_m=radius)

    async def search(self, c: Criteria) -> list:
        return await self.locations.search(await self.conditions(c))

    async def apply(self, ctx: QueryContext) -> QueryContext:
        ctx.chips = chips_for(ctx.criteria, ctx.labels)
        ctx.results = await self.search(ctx.criteria)
        return ctx


class ConditionRelaxer:
    """«6» 0건이면 이동 → 개봉연도 → 장르 → 구·군 순서로 하나씩 풀어 다시 검색한다(FR-405)."""

    ORDER = ("travel", "years", "genres", "gus")

    def __init__(self, searcher: TemplateSearcher):
        self.searcher = searcher

    @staticmethod
    def _has(c: Criteria, name: str) -> bool:
        return {
            "travel": c.base_kind is not None,
            "years": c.year_from is not None or c.year_to is not None,
            "genres": bool(c.genres),
            "gus": bool(c.gus),
        }[name]

    async def apply(self, ctx: QueryContext) -> QueryContext:
        if ctx.results:
            return ctx
        c = ctx.criteria
        for name in self.ORDER:
            if not self._has(c, name):
                continue
            c = c.without(name)
            ctx.relaxed.append(name)
            ctx.results = await self.searcher.search(c)
            if ctx.results:
                ctx.status = QueryStatus.RELAXED
                return ctx
        ctx.status = QueryStatus.NOT_FOUND
        return ctx


class EvidenceGate:
    """«7» 상위 10건으로 근거 묶음을 만든다. 결과가 없으면 요약을 만들지 않는다(AI-REQ-01)."""

    def __init__(self, works_by_locations: Callable[[list[int]], Awaitable[dict[int, list[WorkBrief]]]]):
        self.works_by_locations = works_by_locations

    async def apply(self, ctx: QueryContext) -> QueryContext:
        top = ctx.results[:SUMMARY_TOP]
        if not top:
            ctx.evidence = None
            return ctx
        if isinstance(top[0], LocationHit):
            works = await self.works_by_locations([h.id for h in top])
            items = [
                {
                    "rank": i + 1, "id": h.id, "source_id": ",".join(h.source_ids), "name": h.name, "gu": h.gu,
                    "works": [w.title for w in works.get(h.id, [])][:5],
                    **({"minutes": round(h.travel_min)} if h.travel_min is not None else {}),
                    **({"distance_m": round(h.dist_m)} if h.dist_m is not None else {}),
                }
                for i, h in enumerate(top)
            ]  # fmt: skip
        else:
            items = [
                {"rank": i + 1, "id": w.id, "source_id": ",".join(w.source_ids), "title": w.title,
                 "year": w.release_year, "location_count": w.location_count}
                for i, w in enumerate(top)
            ]  # fmt: skip
        ctx.evidence = {"total": len(ctx.results), "conditions": [ch.label for ch in ctx.chips], "results": items}
        return ctx


class ResultSummarizer:
    """«8» summarize_results. 실패하면 요약 없이 결과만(ERR-003)."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def apply(self, ctx: QueryContext) -> QueryContext:
        if ctx.evidence is None:
            return ctx
        try:
            result = await self.llm.generate(
                "summarize_results", {"evidence": ctx.evidence, "user_input": ctx.masked}, ctx.deadline
            )
        except AIUnavailable as e:
            log.info("summarize_results unavailable", extra={"reasons": e.reasons})
            return ctx
        ctx.summary = result.data.get("sentences", [])  # 다음 단계에서 검증한다
        return ctx


class GroundingCheck:
    """«9» 요약 문장을 근거와 대조해 지운다(FR-407). 남은 문장이 없으면 요약 없이."""

    def __init__(self, lexicon: Callable[[], Awaitable[EntityLexicon]], phrases: PhraseFilter):
        self.lexicon = lexicon
        self.phrases = phrases

    async def apply(self, ctx: QueryContext) -> QueryContext:
        if not ctx.summary:
            ctx.summary = []
            return ctx
        checked = GroundingVerifier(await self.lexicon(), self.phrases).verify(ctx.summary, ctx.evidence)
        ctx.summary = checked.texts[:SUMMARY_MAX]
        ctx.summary_dropped = len(checked.dropped)
        return ctx


class QueryPipeline:
    def __init__(self, steps: list[QueryStep]):
        self.steps = steps

    async def run(self, ctx: QueryContext) -> QueryContext:
        for step in self.steps:
            if ctx.status in STOP:
                break
            ctx = await step.apply(ctx)
        return ctx


class AllowedValues:
    """조건 추출 프롬프트와 사전 대조에 쓰는 허용 값(API-007과 같은 목록). 장르는 ttl_s마다 다시 읽는다."""

    def __init__(self, genres: Callable[[], Awaitable[list[str]]], districts: list[str], ttl_s: float = 600):
        self.genres = genres
        self.districts = list(districts)
        self.ttl_s = ttl_s
        self._cached: tuple[float, list[str]] | None = None

    async def __call__(self) -> dict:
        now = time.monotonic()
        if self._cached is None or now - self._cached[0] > self.ttl_s:
            self._cached = (now, await self.genres())
        return {"genres": self._cached[1], "districts": self.districts}
