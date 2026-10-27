"""앱 생성과 의존성 연결. uvicorn app.main:app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.assembler import Assembler
from app.api.errors import install_error_handlers
from app.api.middleware import JsonlLog, RequestLogger, SessionHeader
from app.api.ratelimit import TokenBucketLimiter
from app.api.routers import health, locations
from app.config import Settings, get_settings
from app.data.db import make_pool
from app.data.repositories.location import LocationRepository
from app.data.repositories.source import SourceRepository
from app.data.repositories.station import StationRepository
from app.data.repositories.work import WorkRepository
from app.services.map.service import MapService
from app.support.sources import SourceRegistry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    pool = make_pool(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await pool.open(wait=False)
        yield
        await pool.close()

    app = FastAPI(title="부산 씨네로케 API", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.pool = pool
    app.state.ai_limiter = TokenBucketLimiter(settings.ai_rate_per_min)
    app.state.ai_breakers = {}  # WP-06 AI 게이트웨이가 공급자별 차단기 상태로 채운다
    app.state.map_service = MapService(LocationRepository(pool), StationRepository(pool), WorkRepository(pool))
    # 출처 대장은 처음 쓸 때 읽는다(Assembler). 시작 때 DB가 늦게 떠도 앱은 뜬다
    app.state.assembler = Assembler(SourceRegistry(SourceRepository(pool)))

    install_error_handlers(app)
    # add_middleware는 나중에 넣은 것이 바깥이다: RequestLogger → SessionHeader → 라우터
    app.add_middleware(SessionHeader)
    app.add_middleware(RequestLogger, log=JsonlLog(settings.log_dir))

    app.include_router(health.router)
    app.include_router(locations.router)
    return app


app = create_app()
