"""오류 형식 {error: {code, message, retry_after}}과 ERR 코드(SDD 8장)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

# 코드 → (상태, 기본 문구). 강등처럼 200으로 끝나는 코드(ERR-003~008·010·013·014)는 여기 두지 않는다.
ERRORS: dict[str, tuple[int, str]] = {
    "ERR-001": (422, "입력 값을 확인해 주세요"),
    "ERR-002": (403, "이용 안내를 먼저 확인해 주세요"),
    "ERR-009": (409, "이 촬영지는 방문 인증을 할 수 없습니다"),
    "ERR-011": (429, "잠시 후 다시 시도해 주세요"),
    "ERR-012": (401, "관리자 인증에 실패했습니다"),
    "ERR-015": (503, "데이터베이스에 연결할 수 없습니다"),
    "ERR-016": (500, "서버 오류가 발생했습니다"),
}


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        status: int | None = None,
        retry_after: int | None = None,
        detail: list | None = None,
    ):
        default_status, default_message = ERRORS[code]
        self.code = code
        self.status = status or default_status
        self.message = message or default_message
        self.retry_after = retry_after
        self.detail = detail
        super().__init__(code)


def error_body(code: str, message: str, retry_after: int | None = None, **extra) -> dict:
    return {"error": {"code": code, "message": message, "retry_after": retry_after, **extra}}


def _respond(request: Request, status: int, body: dict, headers: dict | None = None) -> JSONResponse:
    request.state.error_code = body["error"]["code"]
    return JSONResponse(body, status_code=status, headers=headers)


async def _app_error(request: Request, exc: AppError) -> JSONResponse:
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after is not None else None
    extra = {"detail": exc.detail} if exc.detail else {}
    return _respond(request, exc.status, error_body(exc.code, exc.message, exc.retry_after, **extra), headers)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # 필드 경로와 오류 종류만 돌려준다. 입력 값(좌표·원문)은 응답과 로그에 남기지 않는다.
    detail = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
    return _respond(request, 422, error_body("ERR-001", ERRORS["ERR-001"][1], detail=detail))


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # 404·405처럼 SDD 8장에 코드가 없는 HTTP 오류도 같은 형식으로 감싼다.
    return _respond(request, exc.status_code, error_body(f"HTTP-{exc.status_code}", str(exc.detail)))


async def _db_error(request: Request, exc: Exception) -> JSONResponse:
    return _respond(request, 503, error_body("ERR-015", ERRORS["ERR-015"][1]))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(OperationalError, _db_error)
    app.add_exception_handler(PoolTimeout, _db_error)
    # 처리하지 못한 오류(ERR-016)는 middleware.RequestLogger가 받는다.
