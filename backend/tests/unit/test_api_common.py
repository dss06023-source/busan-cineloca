"""WP-01 공통 처리: 오류 형식, 요청 로그, 세션 헤더, NoticeCheck·RateLimiter, DB 장애 시 상태 확인."""

import json
import uuid

import httpx
import pytest
from fastapi import Depends
from pydantic import BaseModel, Field

from app.api.deps import ai_guard
from app.config import Settings
from app.main import create_app

SID = str(uuid.uuid4())


class Body(BaseModel):
    text: str = Field(max_length=200)


@pytest.fixture
def app(tmp_path):
    # 닿지 않는 DB: 연결 거부가 바로 나도록 1번 포트
    app = create_app(
        Settings(database_url="postgresql://x:y@127.0.0.1:1/none?connect_timeout=1", log_dir=str(tmp_path))
    )
    app.state.pool._timeout = 1.0

    @app.post("/api/_ai", dependencies=[Depends(ai_guard)])
    async def ai_route(body: Body):
        return {"ok": True}

    @app.get("/api/_boom")
    async def boom():
        raise RuntimeError("secret 010-1234-5678")

    return app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


def log_lines(tmp_path) -> list[dict]:
    return [json.loads(line) for f in tmp_path.glob("api-*.jsonl") for line in f.read_text().splitlines()]


async def test_notice_header_required(client):
    r = await client.post("/api/_ai", json={"text": "부산행"}, headers={"X-Session-Id": SID})
    assert r.status_code == 403
    assert r.json() == {"error": {"code": "ERR-002", "message": r.json()["error"]["message"], "retry_after": None}}


async def test_session_header_required_for_ai(client):
    r = await client.post("/api/_ai", json={"text": "부산행"}, headers={"X-Notice-Version": "2026-11-01"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "ERR-001"


async def test_ai_rate_limit_five_per_minute(client):
    headers = {"X-Session-Id": SID, "X-Notice-Version": "2026-11-01"}
    codes = [(await client.post("/api/_ai", json={"text": "a"}, headers=headers)).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    r = await client.post("/api/_ai", json={"text": "a"}, headers=headers)
    assert r.json()["error"]["code"] == "ERR-011"
    assert int(r.headers["Retry-After"]) >= 1
    # 다른 세션은 따로 센다
    other = {"X-Session-Id": str(uuid.uuid4()), "X-Notice-Version": "2026-11-01"}
    assert (await client.post("/api/_ai", json={"text": "a"}, headers=other)).status_code == 200


async def test_validation_error_hides_input(client, tmp_path):
    headers = {"X-Session-Id": SID, "X-Notice-Version": "2026-11-01"}
    secret = "가" * 201
    r = await client.post("/api/_ai", json={"text": secret}, headers=headers)
    assert r.status_code == 422
    body = r.json()
    assert body["error"]["code"] == "ERR-001"
    assert body["error"]["detail"][0]["loc"] == ["body", "text"]
    assert secret not in r.text
    assert secret not in "".join(f.read_text() for f in tmp_path.glob("*.jsonl"))


async def test_unhandled_error_is_err016_with_request_id(client, tmp_path):
    r = await client.get("/api/_boom")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "ERR-016"
    assert err["request_id"] == r.headers["x-request-id"]
    assert "010-1234-5678" not in r.text


async def test_unknown_route_uses_error_format(client):
    r = await client.get("/api/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "HTTP-404"


async def test_request_log_has_template_and_no_query(client, tmp_path):
    await client.get("/api/nope?lat=35.1579&lon=129.0594")
    await client.post("/api/_ai", json={"text": "a"}, headers={"X-Session-Id": SID})
    lines = log_lines(tmp_path)
    assert [line["status"] for line in lines] == [404, 403]
    assert lines[1]["route"] == "/api/_ai"
    assert lines[1]["error_code"] == "ERR-002"
    assert set(lines[0]) == {"ts", "request_id", "method", "route", "status", "ms", "error_code"}
    assert "35.1579" not in json.dumps(lines)


async def test_health_reports_db_down_as_503(client):
    r = await client.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"db": "down", "ai_breakers": {}, "gemini_usage": None}


async def test_unhandled_error_trace_is_scrubbed(client, tmp_path):
    await client.get("/api/_boom")
    line = log_lines(tmp_path)[-1]
    assert line["status"] == 500 and line["error_code"] == "ERR-016"
    assert "RuntimeError" in line["trace"]
    assert "010-1234-5678" not in line["trace"]
