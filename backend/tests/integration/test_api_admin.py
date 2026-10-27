"""API-020~023을 미니 시드 DB로 호출한다. 비밀번호·해시는 테스트 전용 값."""

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
async def setup(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    with psycopg.connect(fresh_db, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO review_item(kind, target_type, target_id, proposal, proposer, model) VALUES"
            " ('tag', 'location', 9, '{\"tags\": [\"야경\", \"역\"]}', 'ai', 'fake'),"
            " ('tag', 'location', 10, '{\"tags\": [\"골목\"]}', 'rule', NULL),"
            " ('match', 'work', 2, '{\"kmdb_id\": \"K99999\", \"title\": \"남포동 블루스\"}', 'rule', NULL)"
        )
    pw_hash = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PW)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path), ai_providers="fake",
                              admin_password_hash=pw_hash))  # fmt: skip
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://t", headers=H)
    async with app.router.lifespan_context(app), client as c:
        yield c, fresh_db, tmp_path


async def login(c):
    r = await c.post("/api/admin/session", json={"password": PW})
    assert r.status_code == 204
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=strict" in r.headers["set-cookie"].lower()


async def test_requires_login_and_locks(setup):
    c, _, logs = setup
    assert (await c.get("/api/admin/reviews")).json()["error"]["code"] == "ERR-012"
    for _ in range(5):
        assert (await c.post("/api/admin/session", json={"password": "nope"})).status_code == 401
    r = await c.post("/api/admin/session", json={"password": PW})
    assert r.status_code == 423 and r.headers["retry-after"]
    text = "".join(p.read_text(encoding="utf-8") for p in logs.glob("*.jsonl"))
    assert PW not in text and "nope" not in text


async def test_review_queue_and_location_edit(setup):
    c, db, _ = setup
    await login(c)
    items = (await c.get("/api/admin/reviews")).json()["items"]
    assert [(i["kind"], i["target_label"]) for i in items] == [
        ("tag", "부산역 광장"), ("tag", "초량 이바구길"), ("match", "남포동 블루스")
    ]  # fmt: skip
    tag9, tag10, match = (i["id"] for i in items)

    # 관리자가 고친 태그로 승인 → 촬영지 태그에 반영(BR-04)
    r = await c.patch("/api/admin/reviews", json={"id": tag9, "action": "approve", "edit": {"tags": ["야경", "광장"]}})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert (await c.patch("/api/admin/reviews", json={"id": tag10, "action": "reject"})).json()["status"] == "rejected"
    assert (await c.patch("/api/admin/reviews", json={"id": tag10, "action": "approve"})).status_code == 404
    assert (await c.patch("/api/admin/reviews", json={"id": match, "action": "approve"})).status_code == 200
    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT tags FROM location WHERE id = 9").fetchone()[0] == ["광장", "야경", "역"]
        assert conn.execute("SELECT tags FROM location WHERE id = 10").fetchone()[0] == ["골목", "전망"]
        assert conn.execute("SELECT kmdb_id, match_status FROM work WHERE id = 2").fetchone() == ("K99999", "reviewed")
    assert (await c.get("/api/admin/reviews")).json()["items"] == []

    r = await c.patch("/api/admin/locations/9", json={"caution": "private", "cert_radius_m": 150})
    assert r.status_code == 200 and (r.json()["caution"], r.json()["cert_radius_m"]) == ("private", 150)
    assert (await c.patch("/api/admin/locations/9", json={"cert_radius_m": 40})).status_code == 422
    assert (await c.patch("/api/admin/locations/999", json={"caution": "none"})).status_code == 404
    # 촬영지 상세(API-006)에 바로 반영: 사유지라 인증 불가
    d = (await c.get("/api/locations/9")).json()
    assert d["certifiable"] is False and d["cert_block_reason"] == "private"


async def test_bad_tag_edit_keeps_item_pending(setup):
    c, _, _ = setup
    await login(c)
    first = (await c.get("/api/admin/reviews", params={"kind": "tag"})).json()["items"][0]["id"]
    r = await c.patch("/api/admin/reviews", json={"id": first, "action": "approve", "edit": {"tags": []}})
    assert r.status_code == 422
    assert first in [i["id"] for i in (await c.get("/api/admin/reviews")).json()["items"]]


async def test_sync_request_is_deduplicated_and_reported(setup):
    c, _, _ = setup
    await login(c)
    a = (await c.post("/api/admin/sync")).json()["run_id"]
    b = (await c.post("/api/admin/sync")).json()["run_id"]
    assert a == b
    rep = (await c.get("/api/admin/sync")).json()
    assert rep["runs"][0]["id"] == a and rep["runs"][0]["status"] == "requested" and rep["usage"] == {}
    await c.delete("/api/admin/session")
    assert (await c.get("/api/admin/sync")).status_code == 401
