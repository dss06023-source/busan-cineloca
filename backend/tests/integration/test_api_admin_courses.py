"""API-024 추천 코스 후보 생성·수정·승인(FR-614)을 미니 시드 DB로 호출한다. 비밀번호·해시는 테스트 전용 값."""

from pathlib import Path

import httpx
import psycopg
import pytest
from argon2 import PasswordHasher

from app.config import Settings
from app.data.seed import load
from app.main import create_app

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
H = {"X-Session-Id": "6f1c2d1e-8b7a-4c1e-9a52-0d2f3b4c5a6e"}
PW = "test-only-password"


@pytest.fixture
async def client(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    pw_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PW)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path), ai_providers="fake",
                              admin_password_hash=pw_hash))  # fmt: skip
    c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://t", headers=H)
    async with app.router.lifespan_context(app), c:
        yield c, fresh_db


async def test_requires_login(client):
    c, _ = client
    assert (await c.get("/api/admin/courses")).json()["error"]["code"] == "ERR-012"
    assert (await c.post("/api/admin/courses", json={"theme": "area", "ref": "중구"})).status_code == 401


async def test_draft_edit_approve(client):
    c, db = client
    assert (await c.post("/api/admin/session", json={"password": PW})).status_code == 204

    r = await c.post("/api/admin/courses", json={"theme": "area", "ref": "중구"})
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "draft" and d["title"] == "중구 촬영지 산책"
    assert 3 <= len(d["stops"]) <= 5 and all(s["name"] for s in d["stops"])
    assert d["total_min"] >= 20 * len(d["stops"]) and not d["start_label"].endswith("역역")
    # 초안은 사용자 목록에 없다
    assert d["id"] not in [x["id"] for x in (await c.get("/api/courses")).json()["items"]]

    w = (await c.post("/api/admin/courses", json={"theme": "work", "ref": "3"})).json()
    assert w["title"] == "「부산 추격전」 따라 걷기"
    p = (await c.post("/api/admin/courses", json={"theme": "actor", "ref": "1"})).json()
    assert p["title"] == "강도윤 출연작 촬영지" and len(p["stops"]) >= 3

    order = [s["location_id"] for s in d["stops"]][::-1][:3]
    e = (await c.patch("/api/admin/courses", json={"id": d["id"], "stops": order, "title": "원도심 한 바퀴"})).json()
    assert [s["location_id"] for s in e["stops"]] == order and e["title"] == "원도심 한 바퀴"

    a = (await c.patch("/api/admin/courses", json={"id": d["id"], "status": "approved"})).json()
    assert a["status"] == "approved"
    assert d["id"] in [x["id"] for x in (await c.get("/api/courses")).json()["items"]]
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT approved_by FROM course WHERE id = %s", (d["id"],)).fetchone()[0] == "admin"

    # 승인된 코스의 장소를 바꾸면 초안으로 돌아가 다시 승인해야 한다
    back = (await c.patch("/api/admin/courses", json={"id": d["id"], "stops": order[:2] + [9]})).json()
    assert back["status"] == "draft"
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT approved_by FROM course WHERE id = %s", (d["id"],)).fetchone()[0] is None

    listed = (await c.get("/api/admin/courses")).json()["items"]
    assert {x["status"] for x in listed} == {"draft", "approved"} and len(listed) == 6


async def test_invalid_inputs(client):
    c, _ = client
    await c.post("/api/admin/session", json={"password": PW})
    assert (await c.post("/api/admin/courses", json={"theme": "area", "ref": "없는구"})).status_code == 422
    assert (await c.post("/api/admin/courses", json={"theme": "work", "ref": "9999"})).status_code == 404
    assert (await c.post("/api/admin/courses", json={"theme": "actor", "ref": "abc"})).status_code == 422
    assert (await c.patch("/api/admin/courses", json={"id": 1, "stops": [9, 7]})).status_code == 422
    assert (await c.patch("/api/admin/courses", json={"id": 1, "stops": [9, 9, 7]})).status_code == 422
    assert (await c.patch("/api/admin/courses", json={"id": 999, "status": "approved"})).status_code == 404
