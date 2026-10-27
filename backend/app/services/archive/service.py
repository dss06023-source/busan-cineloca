"""ArchiveService(COMP-03): 작품 목록·상세(API-001·002), KOBIS 관람등급(API-003), AI 작품 소개(API-004)."""

import logging
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.data.ai_gateway.deadline import Deadline
from app.data.ai_gateway.errors import AIUnavailable, ProviderError
from app.data.ai_gateway.gateway import LLMClient
from app.data.models import MovieInfo, Page, WorkBrief, WorkDetail, WorkQuery
from app.data.repositories.dictionary import DictionaryRepository
from app.data.repositories.work import WorkRepository
from app.support.grounding import EntityLexicon, GroundingVerifier, PhraseFilter

log = logging.getLogger(__name__)

KMDB_SOURCE = "DATA-04"
KOBIS_SOURCE = "DATA-05"
AI_SOURCE = "DATA-11"
RATING_TIMEOUT_S = 3.0  # FR-107
MIN_SENTENCES = 2  # FR-110: 남은 문장이 이보다 적으면 원문으로 강등
LEXICON_TTL_S = 600

Spoiler = Literal["none", "partial"]


class NotFound(Exception):
    pass


class MovieInfoProvider(Protocol):
    """KMDb 실시간 상세(ID_ONLY일 때, WP-05). 실패하면 ProviderError."""

    async def detail(self, kmdb_id: str) -> MovieInfo: ...


class RatingProvider(Protocol):
    """KOBIS 관람등급 실시간(WP-05). 결과를 저장하지 않는다(DATA-05)."""

    async def rating(self, movie_cd: str, timeout_s: float) -> str | None: ...


@dataclass(frozen=True)
class WorkView:
    detail: WorkDetail
    info: MovieInfo | None
    related: list[WorkBrief]
    source_ids: list[str]


@dataclass(frozen=True)
class IntroResult:
    status: Literal["ok", "degraded"]
    sentences: list[str]
    fallback: dict | None
    dropped_count: int
    source_ids: list[str]
    reason: str | None = None

    @property
    def degraded(self) -> bool:
        return self.status == "degraded"


@dataclass
class _Evidence:
    bundle: dict
    source_ids: list[str] = field(default_factory=list)


class NoSpoilerEvidence:
    """'없음' 단계: 장르·감독·출연·키워드·촬영지. 줄거리는 넣지 않는다(FR-109, AI-REQ-07)."""

    spoiler: Spoiler = "none"

    def build(self, d: WorkDetail, info: MovieInfo | None) -> _Evidence:
        w = d.work
        work = {
            "id": w.id,
            "source_id": w.source_id,
            "title": w.title,
            "year": w.release_year,
            "genres": w.genres,
            "directors": [p.name for p in d.people if p.role == "director"],
            "actors": [p.name for p in d.people if p.role == "actor"],
        }
        sources = [w.source_id]
        if info and info.keywords:
            work["keywords"] = info.keywords
            sources.append(info.source_id)
        self._extra(work, info, sources)
        locations = [{"id": loc.id, "source_id": loc.source_id, "name": loc.name, "gu": loc.gu} for loc in d.locations]
        sources += [loc.source_id for loc in d.locations]
        return _Evidence({"spoiler": self.spoiler, "work": work, "locations": locations}, list(dict.fromkeys(sources)))

    def _extra(self, work: dict, info: MovieInfo | None, sources: list[str]) -> None:
        pass


class PartialSpoilerEvidence(NoSpoilerEvidence):
    """'일부' 단계: 위에 원문 줄거리를 더한다."""

    spoiler: Spoiler = "partial"

    def _extra(self, work: dict, info: MovieInfo | None, sources: list[str]) -> None:
        if info and info.plot:
            work["plot"] = info.plot
            sources.append(info.source_id)


EVIDENCE = {"none": NoSpoilerEvidence(), "partial": PartialSpoilerEvidence()}


def info_from_stored(kmdb: dict | None) -> MovieInfo | None:
    """work.kmdb 저장본(STORE일 때)을 MovieInfo로. 키 이름은 우리가 저장할 때 정한 것이다."""
    if not kmdb:
        return None
    return MovieInfo(
        source_id=kmdb.get("source_id", KMDB_SOURCE),
        plot=kmdb.get("plot"),
        keywords=list(kmdb.get("keywords", [])),
        posters=list(kmdb.get("posters", [])),
        stills=list(kmdb.get("stills", [])),
        vods=list(kmdb.get("vods", [])),
        link=kmdb.get("link"),
    )


class ArchiveService:
    def __init__(
        self,
        works: WorkRepository,
        dictionary: DictionaryRepository,
        llm: LLMClient,
        phrases: PhraseFilter,
        movie_info: MovieInfoProvider | None = None,
        ratings: RatingProvider | None = None,
        clock=time.monotonic,
    ):
        self.works = works
        self.dictionary = dictionary
        self.llm = llm
        self.phrases = phrases
        self.movie_info = movie_info
        self.ratings = ratings
        self.clock = clock
        self._lexicon: tuple[float, EntityLexicon] | None = None

    async def list_works(self, query: WorkQuery) -> Page:
        return await self.works.page(query)

    async def _detail(self, work_id: int) -> tuple[WorkDetail, MovieInfo | None]:
        d = await self.works.get(work_id)
        if d is None:
            raise NotFound(work_id)
        info = info_from_stored(d.kmdb)
        if info is None and self.movie_info and d.work.kmdb_id:
            try:
                info = await self.movie_info.detail(d.work.kmdb_id)
            except ProviderError as e:  # ERR-007: 저장된 기본 항목만
                log.info("kmdb detail failed", extra={"provider": "kmdb", "error_code": type(e).__name__})
        return d, info

    async def get_work(self, work_id: int) -> WorkView:
        d, info = await self._detail(work_id)
        related = await self.works.related(work_id)
        sources = [*d.source_ids, *([info.source_id] if info else [])]
        return WorkView(d, info, related, list(dict.fromkeys(sources)))

    async def get_rating(self, work_id: int) -> tuple[str | None, list[str]]:
        """KOBIS 3초 제한. 실패·시간 초과는 rating=None(ERR-006)."""
        d = await self.works.get(work_id)
        if d is None:
            raise NotFound(work_id)
        if not (self.ratings and d.work.kobis_movie_cd):
            return None, []
        try:
            rating = await self.ratings.rating(d.work.kobis_movie_cd, RATING_TIMEOUT_S)
        except ProviderError as e:
            log.info("kobis rating failed", extra={"provider": "kobis", "error_code": type(e).__name__})
            return None, []
        return rating, [KOBIS_SOURCE] if rating else []

    async def lexicon(self) -> EntityLexicon:
        now = self.clock()
        if self._lexicon is None or now - self._lexicon[0] > LEXICON_TTL_S:
            self._lexicon = (now, EntityLexicon(await self.dictionary.lexicon()))
        return self._lexicon[1]

    async def get_intro(self, work_id: int, spoiler: Spoiler, deadline: Deadline) -> IntroResult:
        d, info = await self._detail(work_id)
        ev = EVIDENCE[spoiler].build(d, info)
        fallback = {
            "plot": info.plot if info else None,
            "locations": [{"id": loc.id, "name": loc.name, "gu": loc.gu} for loc in d.locations],
        }

        def degrade(reason: str, dropped: int = 0) -> IntroResult:
            return IntroResult("degraded", [], fallback, dropped, ev.source_ids, reason)

        verifier = GroundingVerifier(await self.lexicon(), self.phrases)
        if not verifier.gate(ev.bundle["locations"]) and not verifier.gate(ev.bundle["work"].get("plot")):
            return degrade("no_evidence")  # 촬영지도 줄거리도 없으면 부르지 않는다(AI-REQ-01)
        try:
            result = await self.llm.generate("work_intro", ev.bundle, deadline)
        except AIUnavailable as e:
            log.info("work_intro unavailable", extra={"reasons": e.reasons})
            return degrade("ai_unavailable")
        checked = verifier.verify(result.data.get("sentences", []), ev.bundle)  # 두 단계 모두 표현 검사(FR-111)
        if len(checked.sentences) < MIN_SENTENCES:
            return degrade("grounding", len(checked.dropped))  # ERR-005
        return IntroResult("ok", checked.texts, None, len(checked.dropped), [*ev.source_ids, AI_SOURCE])
