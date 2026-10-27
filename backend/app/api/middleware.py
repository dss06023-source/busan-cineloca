"""요청 공통 처리(build-plan 5장 '요청 하나가 지나는 순서').

RequestLogger → SessionHeader는 ASGI 미들웨어로, NoticeCheck → RateLimiter는 AI 라우터의
의존성(deps.ai_guard)으로 둔다. 의존성에서 던진 AppError는 오류 처리기를 그대로 탄다.
"""

import json
import time
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.errors import ERRORS, error_body
from app.support.privacy import scrub


class JsonlLog:
    """logs/api-YYYY-MM-DD.jsonl에 한 줄씩 쓴다. 7일 지난 파일 정리는 운영 스크립트가 한다."""

    def __init__(self, directory: str):
        self.dir = Path(directory)

    def write(self, record: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"api-{datetime.now(UTC):%Y-%m-%d}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(scrub(record), ensure_ascii=False) + "\n")


class RequestLogger:
    """요청 ID를 붙이고, 끝나면 경로 템플릿·상태·응답 시간·오류 코드만 기록한다.

    좌표, 입력 원문, 쿼리 문자열, IP, 헤더 값은 남기지 않는다(SDD 8장 로그 정책).
    """

    def __init__(self, app: ASGIApp, log: JsonlLog):
        self.app = app
        self.log = log

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex[:16]
        state = scope.setdefault("state", {})
        state["request_id"] = request_id
        status = 500
        started = time.perf_counter()
        trace = None

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                state["response_started"] = True
                message.setdefault("headers", []).append((b"x-request-id", request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            # 처리하지 못한 오류(ERR-016): 500과 요청 ID를 돌려주고, 스택 추적은 정제해서 로그에만 남긴다.
            status = 500
            state["error_code"] = "ERR-016"
            trace = traceback.format_exc(limit=8)
            if not state.get("response_started"):
                await JSONResponse(
                    error_body("ERR-016", ERRORS["ERR-016"][1], request_id=request_id),
                    status_code=500,
                    headers={"x-request-id": request_id},
                )(scope, receive, send)
        finally:
            route = scope.get("route")
            self.log.write(
                {
                    "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
                    "request_id": request_id,
                    "method": scope["method"],
                    "route": getattr(route, "path", "unmatched"),
                    "status": status,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                    "error_code": state.get("error_code"),
                    **({"trace": trace} if trace else {}),
                }
            )


class SessionHeader:
    """X-Session-Id(탭마다 만든 UUID)를 읽어 request.state.session_id에 둔다. 형식이 틀리면 None."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            raw = dict(scope["headers"]).get(b"x-session-id", b"").decode("latin-1")
            try:
                session_id = str(uuid.UUID(raw))
            except ValueError:
                session_id = None
            scope.setdefault("state", {})["session_id"] = session_id
        await self.app(scope, receive, send)
