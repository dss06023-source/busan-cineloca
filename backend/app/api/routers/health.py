"""API-025 상태 확인."""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg_pool import AsyncConnectionPool, PoolTimeout
from pydantic import BaseModel

from app.api.deps import get_pool
from app.data.repositories import health as repo

router = APIRouter(tags=["상태"])

# Gemini 하루 한도는 미국 태평양 시간 자정에 초기화된다(build-plan 6장).
_PACIFIC = ZoneInfo("America/Los_Angeles")


class HealthOut(BaseModel):
    db: str
    ai_breakers: dict[str, str]
    gemini_usage: dict[str, int] | None


@router.get("/api/health", response_model=HealthOut, responses={503: {"model": HealthOut}})
async def health(request: Request, pool: AsyncConnectionPool = Depends(get_pool)):
    usage = None
    try:
        await repo.ping(pool)
        db = "ok"
        usage = await repo.usage_for(pool, datetime.now(_PACIFIC).date(), "gemini:")
    except (OperationalError, PoolTimeout):
        db = "down"
    body = HealthOut(db=db, ai_breakers=request.app.state.llm.breaker_states(), gemini_usage=usage)
    return JSONResponse(body.model_dump(), status_code=200 if db == "ok" else 503)
