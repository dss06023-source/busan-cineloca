"""앱 생성과 의존성 연결. uvicorn app.main:app"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.assembler import Assembler
from app.api.errors import install_error_handlers
from app.api.middleware import JsonlLog, RequestLogger, SessionHeader
from app.api.ratelimit import TokenBucketLimiter
from app.api.routers import health, locations, query, sources, works
from app.config import Settings, get_settings
from app.data.ai_gateway.factory import build_embedder, build_llm_client
from app.data.db import make_pool
from app.data.repositories.dictionary import DictionaryRepository
from app.data.repositories.location import LocationRepository
from app.data.repositories.source import SourceRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.work import WorkRepository
from app.pipeline.query import steps as qs
from app.services.archive.service import ArchiveService
from app.services.map.service import DISTRICTS, MapService
from app.services.query.service import QueryService, SessionStore
from app.support.grounding import LexiconCache, PhraseFilter
from app.support.sources import SourceRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    pool = make_pool(settings.database_url)
    http = httpx.AsyncClient()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await pool.open(wait=False)
        yield
        await http.aclose()
        await pool.close()

    app = FastAPI(title="부산 씨네로케 API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.pool = pool
    app.state.ai_limiter = TokenBucketLimiter(settings.ai_rate_per_min)
    app.state.llm = build_llm_client(settings, pool, http)
    app.state.embedder = build_embedder(settings, http)
    # KMDb 실시간 상세·KOBIS 등급 공급자는 WP-05가 연결한다. 없으면 저장된 항목만, 등급은 null
    phrases = PhraseFilter.from_config()
    work_repo, dictionary = WorkRepository(pool), DictionaryRepository(pool)
    locs, stations = LocationRepository(pool), StationRepository(pool)
    app.state.archive_service = ArchiveService(work_repo, dictionary, app.state.llm, phrases)
    app.state.query_service = _query_service(settings, app.state.llm, app.state.embedder, work_repo, dictionary, locs,
                                             stations, phrases)  # fmt: skip
    app.state.map_service = MapService(locs, stations, work_repo)
    # 출처 대장은 처음 쓸 때 읽는다(Assembler). 시작 때 DB가 늦게 떠도 앱은 뜬다
    app.state.assembler = Assembler(SourceRegistry(SourceRepository(pool)))

    install_error_handlers(app)
    # add_middleware는 나중에 넣은 것이 바깥이다: RequestLogger → SessionHeader → 라우터
    app.add_middleware(SessionHeader)
    app.add_middleware(RequestLogger, log=JsonlLog(settings.log_dir))

    app.include_router(health.router)
    app.include_router(locations.router)
    app.include_router(works.router)
    app.include_router(query.router)
    app.include_router(sources.router)
    return app


def _query_service(settings, llm, embedder, works, dictionary, locs, stations, phrases) -> QueryService:
    """F4 파이프라인 9단계(SDD CD-03)."""
    allowed = qs.AllowedValues(works.genres, list(DISTRICTS))

    async def work_title(work_id: int) -> str | None:
        d = await works.get(work_id)
        return d.work.title if d else None

    searcher = qs.TemplateSearcher(locs, stations)
    pipeline = qs.QueryPipeline([
        qs.MaskStep(),
        qs.ConditionExtractor(llm, allowed),
        qs.ContextMerger(),
        qs.DictionaryResolver(dictionary, locs, stations, allowed, work_title, embedder),
        searcher,
        qs.ConditionRelaxer(searcher),
        qs.EvidenceGate(works.by_locations),
        qs.ResultSummarizer(llm),
        qs.GroundingCheck(LexiconCache(dictionary.lexicon).get, phrases),
    ])  # fmt: skip
    return QueryService(pipeline, searcher, SessionStore(), llm.config.deadline_s, works.by_locations)


app = create_app()
