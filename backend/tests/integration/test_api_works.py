"""API-001~004를 미니 시드 DB와 FakeProvider로 호출한다(시연 장면 2)."""

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.data.ai_gateway.providers import FakeProvider
from app.data.seed import load
from app.main import create_app

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
AI_HEADERS = {"X-Session-Id": "6f1c2d1e-8b7a-4c1e-9a52-0d2f3b4c5a6e", "X-Notice-Version": "2026-11-01"}


@pytest.fixture
async def app(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path), ai_providers="fake", ai_rate_per_min=100))
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


def fake(app, sentences=None, mode="ok") -> FakeProvider:
    p = FakeProvider({"work_intro": {"sentences": sentences or []}}, mode=mode)
    app.state.llm.providers["fake"] = p
    return p


async def test_list_sort_search_and_paging(client):
    body = (await client.get("/api/works")).json()
    assert body["total"] == 10 and len(body["items"]) == 10 and body["page"] == 1
    counts = [w["location_count"] for w in body["items"]]
    assert counts == sorted(counts, reverse=True)
    years = [w["release_year"] for w in (await client.get("/api/works?sort=year")).json()["items"]]
    assert years == sorted(years, reverse=True)
    found = (await client.get("/api/works", params={"q": "부산 추격"})).json()
    assert [w["title"] for w in found["items"]] == ["부산 추격전"]
    assert (await client.get("/api/works?genre=로맨스")).json()["total"] == 1
    assert (await client.get("/api/works?sort=title")).status_code == 422


async def test_detail_scene2(client):
    res = await client.get("/api/works/3")
    assert res.status_code == 200
    d = res.json()
    assert d["work"]["title"] == "부산 추격전"
    assert any(p["name"] == "강도윤" for p in d["people"])
    assert d["plot"].startswith("형사 강도윤") and d["keywords"] == ["추격", "형사", "부산역"]
    assert d["locations"] and len({loc["id"] for loc in d["locations"]}) == len(d["locations"])
    assert {w["id"] for w in d["related"]} >= {4, 9}  # 강도윤 출연작
    assert 3 not in {w["id"] for w in d["related"]} and len(d["related"]) <= 5
    assert d["images"] == {"posters": [], "stills": []} and d["vod"] == []
    assert "DEV-SEED" in d["source_ids"] and [s["id"] for s in d["sources"]] == d["source_ids"]


async def test_detail_and_rating_404_and_null_rating(client):
    assert (await client.get("/api/works/999")).status_code == 404
    assert (await client.get("/api/works/999/rating")).status_code == 404
    r = (await client.get("/api/works/3/rating")).json()
    assert r == {"rating": None, "source_ids": [], "sources": []}  # KOBIS 공급자 없음 → 등급 없이(ERR-006)


async def test_intro_requires_notice(client):
    res = await client.post("/api/works/3/intro", json={"spoiler": "none"}, headers={"X-Session-Id": "s"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "ERR-002"
    bad = await client.post("/api/works/3/intro", json={"spoiler": "full"}, headers=AI_HEADERS)
    assert bad.status_code == 422


async def location_names(client, work_id):
    return [(loc["name"], loc["gu"]) for loc in (await client.get(f"/api/works/{work_id}")).json()["locations"]]


async def test_intro_ok_grounded(app, client):
    (name, gu), *_ = await location_names(client, 3)
    p = fake(
        app,
        [
            {"text": "「부산 추격전」(2017)은 범죄 액션 영화입니다.", "entities": ["부산 추격전", "2017"]},
            {"text": f"{gu}의 {name}에서 촬영했습니다.", "entities": [gu, name]},
            {"text": "강도윤이 출연합니다.", "entities": ["강도윤"]},
        ],
    )
    res = await client.post("/api/works/3/intro", json={"spoiler": "none"}, headers=AI_HEADERS)
    body = res.json()
    assert res.status_code == 200 and body["status"] == "ok" and body["ai_generated"] and not body["degraded"]
    assert len(body["sentences"]) == 3 and body["fallback"] is None and body["dropped_count"] == 0
    assert "DATA-11" in body["source_ids"] and p.calls == ["work_intro"]


async def test_intro_drops_ungrounded_and_degrades(app, client):
    fake(
        app,
        [
            {"text": "마동석이 주연을 맡았습니다.", "entities": ["마동석"]},
            {"text": "2023년에 개봉했습니다.", "entities": []},
            {"text": "「부산 추격전」은 범죄 영화입니다.", "entities": ["부산 추격전"]},
        ],
    )
    body = (await client.post("/api/works/3/intro", json={"spoiler": "partial"}, headers=AI_HEADERS)).json()
    assert body["status"] == "degraded" and body["degraded"] and not body["ai_generated"]
    assert body["sentences"] == [] and body["dropped_count"] == 2
    assert body["fallback"]["plot"].startswith("형사 강도윤") and body["fallback"]["locations"]


async def test_intro_spoiler_phrase_removed_in_both_levels(app, client):
    (name, gu), *_ = await location_names(client, 3)
    ok = [
        {"text": "「부산 추격전」은 범죄 영화입니다.", "entities": ["부산 추격전"]},
        {"text": f"{name}에서 촬영했습니다.", "entities": [name]},
    ]
    fake(app, [*ok, {"text": "결말에서 강도윤이 증인을 찾아냅니다.", "entities": ["강도윤"]}])
    for spoiler in ("none", "partial"):
        app.state.llm.cache = _NoCache()
        body = (await client.post("/api/works/3/intro", json={"spoiler": spoiler}, headers=AI_HEADERS)).json()
        assert body["status"] == "ok" and len(body["sentences"]) == 2 and body["dropped_count"] == 1


@pytest.mark.parametrize("mode", ["timeout", "429", "500", "bad_schema"])
async def test_intro_ai_failure_degrades(app, client, mode):
    fake(app, mode=mode)
    res = await client.post("/api/works/9/intro", json={"spoiler": "none"}, headers=AI_HEADERS)
    body = res.json()
    assert res.status_code == 200 and body["status"] == "degraded"
    assert body["fallback"]["plot"] and body["fallback"]["locations"]


class _NoCache:
    async def get(self, key):
        return None

    async def put(self, key, task, value, ttl_h=24):
        pass
