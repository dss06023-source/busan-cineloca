"""라우터 공통 의존성."""

from fastapi import Request
from psycopg_pool import AsyncConnectionPool

from app.api.assembler import Assembler
from app.api.errors import AppError
from app.services.archive.service import ArchiveService
from app.services.map.service import MapService
from app.services.query.service import QueryService


def get_pool(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool


def get_map_service(request: Request) -> MapService:
    return request.app.state.map_service


def get_archive_service(request: Request) -> ArchiveService:
    return request.app.state.archive_service


def get_query_service(request: Request) -> QueryService:
    return request.app.state.query_service


def get_assembler(request: Request) -> Assembler:
    return request.app.state.assembler


def session_id(request: Request) -> str | None:
    return request.state.session_id


async def ai_guard(request: Request) -> None:
    """AI를 쓰는 API(API-004·012·013)에만 붙인다: NoticeCheck → RateLimiter."""
    if not request.headers.get("x-notice-version"):
        raise AppError("ERR-002")  # FR-701
    sid = request.state.session_id
    if sid is None:
        raise AppError("ERR-001", "X-Session-Id 헤더가 필요합니다")
    retry_after = request.app.state.ai_limiter.acquire(sid)
    if retry_after is not None:
        raise AppError("ERR-011", retry_after=retry_after)
