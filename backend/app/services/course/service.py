"""CourseService(COMP-05): 추천 코스(API-009·010), 나만의 코스(API-011), AI 맞춤 코스(API-012)."""

import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import Literal

from app.data.ai_gateway.deadline import Deadline
from app.data.ai_gateway.errors import AIUnavailable, ProviderError
from app.data.ai_gateway.gateway import LLMClient
from app.data.models import Course, Location, Point, WorkBrief
from app.data.repositories.course import CourseRepository
from app.data.repositories.dictionary import DictionaryRepository
from app.data.repositories.location import LocationRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.work import WorkRepository
from app.pipeline.course.route import Place, Route, RoutePlanner, TravelModel
from app.pipeline.course.scoring import (
    BudgetFitter,
    Candidate,
    CandidateScorer,
    CourseInfeasible,
    Preference,
    Scored,
    course_config,
)
from app.pipeline.travel import haversine_m, walk_minutes
from app.support.grounding import GroundingVerifier, LexiconCache, PhraseFilter
from app.support.privacy import mask

log = logging.getLogger(__name__)

CUSTOM_MIN, CUSTOM_MAX = 2, 10  # FR-303
DEFAULT_START = "113"  # 부산역
SURE = 0.5
AI_SOURCE = "DATA-11"
STATION_SOURCE = "DATA-08"
TRAVEL_TTL_S = 600


class NotFound(Exception):
    pass


class InvalidInput(ValueError):
    pass


@dataclass(frozen=True)
class Start:
    kind: Literal["station", "location", "point"]
    station_id: str | None = None
    location_id: int | None = None
    point: Point | None = None


@dataclass
class RouteView:
    route: Route
    works: dict[int, list[WorkBrief]]
    gus: dict[int, str | None]
    source_ids: list[str]


@dataclass
class AICourse:
    status: Literal["OK", "FALLBACK", "OUT_OF_SCOPE", "INFEASIBLE"]
    preference: dict = field(default_factory=dict)
    view: RouteView | None = None
    reasons: list[dict] = field(default_factory=list)
    title: str | None = None
    intro: list[str] = field(default_factory=list)
    intro_ai: bool = False
    dropped_count: int = 0
    masked: bool = False
    notices: list[str] = field(default_factory=list)
    reason: str | None = None
    budget_h: float | None = None


def candidate_of(c) -> Candidate:
    place = Place(c.id, c.name, c.lat, c.lon, c.nearest_station_id, c.station_walk_min)
    return Candidate(place, c.gu, c.tags, c.genres, c.work_ids, c.person_ids, c.work_count, c.caution, c.similarity)


def place_of(loc: Location) -> Place:
    return Place(loc.id, loc.name, loc.lat, loc.lon, loc.nearest_station_id, loc.station_walk_min)


class CourseService:
    def __init__(
        self,
        courses: CourseRepository,
        locations: LocationRepository,
        stations: StationRepository,
        works: WorkRepository,
        dictionary: DictionaryRepository,
        llm: LLMClient,
        lexicon: LexiconCache,
        phrases: PhraseFilter,
        embedder=None,
        allowed_genres=None,
    ):
        self.courses = courses
        self.locations = locations
        self.stations = stations
        self.works = works
        self.dictionary = dictionary
        self.llm = llm
        self.lexicon = lexicon
        self.phrases = phrases
        self.embedder = embedder
        self.allowed_genres = allowed_genres or works.genres
        self.conf = course_config()
        self._travel: tuple[float, TravelModel] | None = None

    async def travel(self) -> TravelModel:
        now = time.monotonic()
        if self._travel is None or now - self._travel[0] > TRAVEL_TTL_S:
            stations = await self.stations.all()
            model = TravelModel(await self.stations.time_table(), {s.id: s.line for s in stations})
            self._travel = (now, model)
        return self._travel[1]

    async def planner(self) -> RoutePlanner:
        return RoutePlanner(await self.travel(), self.conf["dwell_min"])

    async def start_place(self, start: Start) -> Place:
        if start.kind == "station":
            s = await self.stations.get(start.station_id)
            if s is None:
                raise InvalidInput("start.station_id")
            return Place(None, f"{s.name}역", s.lat, s.lon, s.id, 0)
        if start.kind == "location":
            locs = await self.locations.many([start.location_id])
            if not locs or locs[0].lat is None:
                raise InvalidInput("start.location_id")
            return place_of(locs[0])
        p = start.point
        s = await self.stations.nearest(p)
        walk = walk_minutes(haversine_m(p.lat, p.lon, s.lat, s.lon)) if s else None
        return Place(None, "현재 위치", p.lat, p.lon, s.id if s else None, walk)

    async def _view(self, route: Route, extra_sources: list[str] | None = None) -> RouteView:
        ids = [p.id for p in route.stops]
        works = await self.works.by_locations(ids)
        gus = {loc.id: loc.gu for loc in await self.locations.many(ids)}
        sources = {"DATA-06", *(extra_sources or [])}
        if any(leg.mode == "subway" for leg in route.legs) or route.start.station_id:
            sources.add(STATION_SOURCE)
        for i in ids:
            sources.update(await self.locations.shooting_sources(i))
        return RouteView(route, works, gus, sorted(sources))

    # 추천 코스 ---------------------------------------------------------------
    async def list_recommended(self, theme: str | None) -> list[tuple[Course, int]]:
        """승인된 추천 코스와 장소 수(FR-301)."""
        return [(c, len(await self.courses.stops(c.id))) for c in await self.courses.approved(theme)]

    async def get_course(self, course_id: int) -> tuple[Course, RouteView]:
        c = await self.courses.get(course_id)
        if c is None or c.status != "approved":
            raise NotFound(course_id)
        start = Point(c.start_lat, c.start_lon)
        s = await self.stations.nearest(start)
        walk = walk_minutes(haversine_m(start.lat, start.lon, s.lat, s.lon)) if s else None
        start_place = Place(None, c.start_label, c.start_lat, c.start_lon, s.id if s else None, walk)
        stops = [place_of(loc) for loc in await self.locations.many([st.location_id for st in c.stops])]
        route = (await self.planner()).plan(start_place, stops, fixed_order=True)
        return c, await self._view(route)

    # 나만의 코스 -------------------------------------------------------------
    async def plan_custom(self, start: Start, location_ids: list[int], fixed_order: bool) -> RouteView:
        ids = list(dict.fromkeys(location_ids))
        if not CUSTOM_MIN <= len(ids) <= CUSTOM_MAX:
            raise InvalidInput("location_ids는 2~10곳")
        locs = await self.locations.many(ids)
        if len(locs) != len(ids) or any(loc.lat is None for loc in locs):
            raise InvalidInput("좌표가 있는 촬영지만 고를 수 있습니다")
        route = (await self.planner()).plan(await self.start_place(start), [place_of(x) for x in locs], fixed_order)
        return await self._view(route)

    # AI 맞춤 코스 ------------------------------------------------------------
    async def allowed(self) -> dict:
        cands = await self.locations.course_candidates()
        tags = sorted({t for c in cands for t in c.tags})
        gus = sorted({c.gu for c in cands if c.gu})
        return {"genres": await self.allowed_genres(), "mood_tags": tags, "districts": gus}

    async def _ids(self, kind: str, names: list[str], notices: list[str]) -> list[int]:
        out = []
        for name in names[:3]:
            hits = [h for h in await self.dictionary.fuzzy(kind, name) if h.score >= SURE]
            if hits:
                out.append(int(hits[0].canonical_id))
            else:
                notices.append(f"'{name}'을(를) 찾지 못해 취향에서 뺐습니다.")
        return out

    async def resolve(self, raw: dict, notices: list[str]) -> Preference:
        allowed = await self.allowed()
        keep = lambda key, allow_key: [v for v in raw.get(key) or [] if v in allowed[allow_key]]  # noqa: E731
        return Preference(
            genres=keep("genres", "genres"),
            mood_tags=keep("mood_tags", "mood_tags"),
            work_ids=await self._ids("work", raw.get("works") or [], notices),
            person_ids=await self._ids("person", raw.get("persons") or [], notices),
            gus=keep("districts", "districts"),
            avoid=[a for a in raw.get("avoid") or [] if isinstance(a, str)][:5],
        )

    async def _start_from_text(self, name: str | None, notices: list[str]) -> Start | None:
        if not name:
            return None
        key = name.strip()
        hits = await self.dictionary.fuzzy("station", key if key.endswith("역") else key + "역")
        if hits and hits[0].score >= SURE:
            return Start("station", station_id=hits[0].canonical_id)
        locs = [h for h in await self.locations.by_name(key) if h.score >= SURE]
        if locs:
            return Start("location", location_id=int(locs[0].canonical_id))
        notices.append(f"출발지 '{name}'을(를) 찾지 못해 부산역에서 출발합니다.")
        return None

    async def plan_ai(
        self,
        deadline: Deadline,
        text: str | None = None,
        manual: dict | None = None,
        start: Start | None = None,
        budget_h: float | None = None,
    ) -> AICourse:
        """취향 문장을 구조화하거나(manual이 없을 때) 직접 고른 조건으로 코스를 만든다(FR-307~312)."""
        notices: list[str] = []
        masked, kinds = mask(text or "")
        raw = manual or {}
        if manual is None:
            allowed = await self.allowed()
            try:
                result = await self.llm.generate(
                    "structure_preference", {"allowed": allowed, "user_input": masked}, deadline
                )
            except AIUnavailable as e:
                log.info("structure_preference unavailable", extra={"reasons": e.reasons})
                return AICourse("FALLBACK", masked=bool(kinds))  # 조건 직접 선택 화면(FR-312)
            raw = result.data
            if raw.get("out_of_scope"):
                return AICourse("OUT_OF_SCOPE", masked=bool(kinds))
        pref = await self.resolve(raw, notices)
        start = start or await self._start_from_text(raw.get("start"), notices) or Start("station", DEFAULT_START)
        budget = budget_h or raw.get("budget_h") or self.conf["default_budget_h"]
        start_place = await self.start_place(start)
        pref_view = {
            **{k: getattr(pref, k) for k in ("genres", "mood_tags", "work_ids", "person_ids", "gus", "avoid")},
            "start": start_place.name,
            "budget_h": budget,
        }

        sim_vec = None
        if text and self.embedder is not None:
            with contextlib.suppress(ProviderError):  # 임베딩이 안 되면 태그 일치만(build-plan 6장)
                sim_vec = (await self.embedder.embed([masked]))[0]
        cands = [candidate_of(c) for c in await self.locations.course_candidates(sim_vec)]
        scored = CandidateScorer().top(cands, pref, start_place)
        try:
            route, chosen = BudgetFitter(await self.planner()).fit(start_place, scored, round(budget * 60))
        except CourseInfeasible as e:
            return AICourse("INFEASIBLE", pref_view, notices=notices, reason=e.reason, masked=bool(kinds))
        view = await self._view(route)
        title, intro, reasons, ai, dropped = await self._narrate(route, chosen, view, deadline)
        if ai:
            view.source_ids = sorted({*view.source_ids, AI_SOURCE})
        return AICourse(
            "OK", pref_view, view, reasons, title, intro, ai, dropped, bool(kinds), notices, budget_h=budget
        )

    async def _narrate(self, route: Route, chosen: list[Scored], view: RouteView, deadline: Deadline):
        """course_intro로 소개와 선정 이유를 받고 근거 대조. 실패하면 템플릿 문장(FR-311)."""
        course = [
            {
                "location_id": p.id, "name": p.name, "gu": view.gus.get(p.id),
                "works": [w.title for w in view.works.get(p.id, [])][:3],
                "stay_min": route.dwell_min, "leg_min": leg.minutes, "leg_mode": leg.mode,
            }
            for p, leg in zip(route.stops, route.legs, strict=True)
        ]  # fmt: skip
        evidence = {"start": route.start.name, "total_min": route.total_min, "course": course}
        template_reasons = [{"location_id": c["location_id"], "text": _reason(c, chosen)} for c in course]
        hours = round(route.total_min / 60, 1)
        template = (
            f"{route.start.name}에서 출발해 {len(course)}곳을 돌아보는 코스",
            [f"{route.start.name}에서 출발해 촬영지 {len(course)}곳을 돌아보는 약 {hours}시간 코스입니다."],
        )
        try:
            result = await self.llm.generate("course_intro", evidence, deadline)
        except AIUnavailable as e:
            log.info("course_intro unavailable", extra={"reasons": e.reasons})
            return template[0], template[1], template_reasons, False, 0
        verifier = GroundingVerifier(await self.lexicon.get(), self.phrases)
        checked = verifier.verify(result.data.get("sentences", []), evidence)
        ids = {c["location_id"] for c in course}
        ai_reasons = {
            r["location_id"]: r["text"]
            for r in result.data.get("reasons", [])
            if r["location_id"] in ids and verifier.verify([{"text": r["text"], "entities": []}], evidence).sentences
        }
        reasons = [{"location_id": r["location_id"], "text": ai_reasons.get(r["location_id"], r["text"])}
                   for r in template_reasons]  # fmt: skip
        if not checked.sentences:
            return template[0], template[1], reasons, False, len(checked.dropped)
        title_ok = verifier.verify([{"text": result.data.get("title", ""), "entities": []}], evidence).sentences
        title = result.data["title"] if title_ok else template[0]
        return title, checked.texts, reasons, True, len(checked.dropped)


def _reason(stop: dict, chosen: list[Scored]) -> str:
    works = stop["works"]
    base = f"「{works[0]}」 촬영지" if works else "부산 촬영지"
    matched = next((s.matched for s in chosen if s.candidate.place.id == stop["location_id"]), [])
    why = {"genres": "좋아하는 장르", "mood_tags": "원하는 분위기", "work_ids": "고른 작품", "person_ids": "고른 인물",
           "gus": "고른 지역"}  # fmt: skip
    return base + (f" · {why[matched[0]]}" if matched else "")
