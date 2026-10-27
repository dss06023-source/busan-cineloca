"""API-016~018을 미니 시드 DB로 호출한다(시연 장면 5). 좌표가 로그·DB에 남지 않는지도 본다."""

import math
from pathlib import Path

import httpx
import psycopg
import pytest
from psycopg import sql

from app.config import Settings
from app.data.seed import load
from app.main import create_app
from app.pipeline.travel import EARTH_R_M

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
H = {"X-Session-Id": "6f1c2d1e-8b7a-4c1e-9a52-0d2f3b4c5a6e"}
# 테스트 전용 키(실제 키 아님)
KEYS = "t2:" + "q" * 32 + ",t1:" + "r" * 32
SPOTS = {9: (35.1152, 129.0422), 7: (35.1557, 129.0598), 12: (35.0966, 129.0306)}


def near(location_id: int, meters: float = 20) -> dict:
    lat, lon = SPOTS[location_id]
    return {"lat": round(lat + math.degrees(meters / EARTH_R_M), 7), "lon": lon}


@pytest.fixture
async def setup(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path), ai_providers="fake", token_keys=KEYS))
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", headers=H)
    async with app.router.lifespan_context(app), client as c:
        yield c, tmp_path, fresh_db


async def certify(c, loc, held=(), meters=20, acc=12.0):
    body = {"location_id": loc, **near(loc, meters), "accuracy_m": acc, "held": list(held)}
    return await c.post("/api/stamps", json=body)


async def test_scene5_certify_verify_and_badge(setup):
    c, logs, db = setup
    tokens = []
    for loc in (9, 7):
        r = await certify(c, loc, tokens)
        assert r.status_code == 200 and r.json()["ok"], r.text
        tokens.append(r.json()["token"])
    dup = (await certify(c, 9, tokens)).json()
    assert dup == {"ok": False, "token": None, "reason": "duplicate", "distance_m": 20}

    v = (await c.post("/api/stamps/verify", json={"tokens": [*tokens, tokens[0][:-2] + "xx"]})).json()
    assert [s["location"]["name"] for s in v["valid"]] == ["부산역 광장", "서면 젊음의거리"]
    assert v["invalid_count"] == 1

    part = (await c.post("/api/badges", json={"course": {"id": 1}, "stamps": tokens})).json()
    assert part["ok"] is False and part["missing"] == [12]
    tokens.append((await certify(c, 12)).json()["token"])
    full = (await c.post("/api/badges", json={"course": {"id": 1}, "stamps": tokens})).json()
    assert full["ok"] and full["course_key"] == "course:1" and full["token"].count(".") == 2
    vb = (await c.post("/api/stamps/verify", json={"tokens": [], "badges": [full["token"]]})).json()
    assert [b["course_key"] for b in vb["badges"]] == ["course:1"] and vb["invalid_count"] == 0
    mine = (await c.post("/api/badges", json={"course": {"location_ids": [7, 9]}, "stamps": tokens})).json()
    assert mine["ok"] and mine["course_key"].startswith("custom:")

    # 위치 미저장 감사(NFR-003): 보낸 좌표가 로그와 DB 어디에도 없다
    sent = [str(near(i)["lat"]) for i in SPOTS]
    text = "".join(p.read_text(encoding="utf-8") for p in logs.glob("*.jsonl"))
    assert text and not any(s in text for s in sent)
    with psycopg.connect(db) as conn:
        tables = [r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
        rows = sql.SQL("SELECT string_agg(t::text, '|') FROM {} t")
        dump = "|".join(str(conn.execute(rows.format(sql.Identifier(t))).fetchone()[0]) for t in tables)
    assert not any(s in dump for s in sent)
    assert not any("stamp" in t or "badge" in t for t in tables)


async def test_certify_failures(setup):
    c, _, _ = setup
    far = (await certify(c, 9, meters=150)).json()
    assert (far["ok"], far["reason"], far["distance_m"]) == (False, "distance", 150)
    blurry = (await certify(c, 9, acc=51)).json()
    assert (blurry["ok"], blurry["reason"]) == (False, "accuracy")
    r = await c.post("/api/stamps", json={"location_id": 21, "lat": 35.1, "lon": 129.0, "accuracy_m": 5, "held": []})
    assert r.status_code == 409 and r.json()["error"]["code"] == "ERR-009"
    assert r.json()["error"]["detail"] == [{"reason": "no_coords"}]
    r = await c.post("/api/stamps", json={"location_id": 999, "lat": 35.1, "lon": 129.0, "accuracy_m": 5})
    assert r.status_code == 404
    r = await c.post("/api/stamps", json={"location_id": 9, "lat": 135.1, "lon": 129.0, "accuracy_m": 5})
    assert r.status_code == 422 and "135.1" not in r.text


async def test_badge_validation(setup):
    c, _, _ = setup
    assert (await c.post("/api/badges", json={"course": {"id": 3}, "stamps": []})).status_code == 404  # 초안
    r = await c.post("/api/badges", json={"course": {}, "stamps": []})
    assert r.status_code == 422
    r = await c.post("/api/badges", json={"course": {"location_ids": [9]}, "stamps": []})
    assert r.status_code == 422 and r.json()["error"]["code"] == "ERR-001"
