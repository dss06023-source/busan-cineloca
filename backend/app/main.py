"""앱 생성과 의존성 연결. uvicorn app.main:app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.middleware import JsonlLog, RequestLogger, SessionHeader
from app.api.ratelimit import TokenBucketLimiter
from app.api.routers import health
from app.config import Settings, get_settings
from app.data.db import make_pool


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

    install_error_handlers(app)
    # add_middleware는 나중에 넣은 것이 바깥이다: RequestLogger → SessionHeader → 라우터
    app.add_middleware(SessionHeader)
    app.add_middleware(RequestLogger, log=JsonlLog(settings.log_dir))

    app.include_router(health.router)
    return app


app = create_app()
