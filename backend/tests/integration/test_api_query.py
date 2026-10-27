"""API-013~015를 미니 시드 DB와 FakeProvider로 호출한다(시연 장면 3, FR-401~412)."""

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.data.ai_gateway.providers import FakeProvider
from app.data.seed import load
from app.main import create_app

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
SID = "6f1c2d1e-8b7a-4c1e-9a52-0d2f3b4c5a6e"
H = {"X-Session-Id": SID, "X-Notice-Version": "2026-11-01"}
SCENE3 = {
    "persons": ["강도윤"],
    "base": {"kind": "station", "name": "지하철역"},
    "travel": {"mode": "walk", "minutes": 10},
    "result_type": "LOCATION",
    "out_of_scope": False,
}


class NoCache:
    async def get(self, key):
        return None

    async def put(self, key, task, value, ttl_h=24):
        pass


@pytest.fixture
async def app(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path), ai_providers="fake", ai_rate_per_min=100))
    app.state.llm.cache = NoCache()
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


def fake(app, extract=None, summary=None, mode="ok") -> FakeProvider:
    p = FakeProvider({"extract_query": extract or SCENE3, "summarize_results": {"sentences": summary or []}}, mode=mode)
    app.state.llm.providers["fake"] = p
    return p


async def ask(client, text="강도윤 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안", **kw):
    return await client.post("/api/query", json={"text": text, **kw}, headers=H)


async def test_scene3(app, client):
    p = fake(
        app,
        summary=[
            {"text": "강도윤 출연작 촬영지 4곳이 역에서 걸어서 10분 안에 있습니다.", "entities": ["강도윤"]},
            {"text": "부산역 광장은 2분 거리입니다.", "entities": ["부산역 광장"]},
            {"text": "해운대해수욕장도 가깝습니다.", "entities": ["해운대해수욕장"]},  # 결과 밖 → 삭제
        ],
    )
    res = await ask(client)
    body = res.json()
    assert res.status_code == 200 and body["status"] == "OK"
    assert [i["name"] for i in body["items"]] == ["부산역 광장", "자갈치시장", "서면 젊음의거리", "영도대교"]
    assert body["items"][0]["travel_min"] == 2 and body["items"][0]["works"]
    assert {c["field"]: c["label"] for c in body["chips"]} == {
        "person_ids": "강도윤",
        "travel": "지하철역에서 걸어서 10분",
    }
    assert body["criteria"]["person_ids"] == [1] and body["criteria"]["base_kind"] == "any_station"
    assert body["summary"]["sentences"][:1] == ["강도윤 출연작 촬영지 4곳이 역에서 걸어서 10분 안에 있습니다."]
    assert body["summary"]["dropped_count"] == 1 and len(body["summary"]["sentences"]) == 2
    assert "DATA-11" in body["source_ids"] and "DATA-08" in body["source_ids"]
    assert p.calls == ["extract_query", "summarize_results"]  # LLM 2회


async def test_masking_and_no_raw_text_to_llm(app, client):
    p = fake(app)
    sent = []
    orig = p.complete

    async def spy(prompt, schema, timeout_s):
        sent.append(prompt.user)
        return await orig(prompt, schema, timeout_s)

    p.complete = spy
    body = (await ask(client, "010-1234-5678 강도윤 촬영지")).json()
    assert body["masked"] is True
    assert all("010-1234-5678" not in u for u in sent) and "[개인정보]" in sent[0]


async def test_follow_up_keeps_context_and_reset(app, client):
    fake(app)
    await ask(client)
    fake(app, extract={"gus": [], "districts": ["중구"], "result_type": "LOCATION", "out_of_scope": False})
    body = (await ask(client, "그중 중구만")).json()
    assert [i["name"] for i in body["items"]] == ["자갈치시장"]
    assert {c["field"] for c in body["chips"]} == {"person_ids", "travel", "gus"}
    assert (await client.delete("/api/query/session", headers=H)).status_code == 204
    body = (await ask(client, "중구만")).json()
    assert {c["field"] for c in body["chips"]} == {"gus"}


async def test_relax_order(app, client):
    fake(app, extract={**SCENE3, "years": {"from": 1990, "to": 1995}})
    body = (await ask(client)).json()
    assert body["status"] == "RELAXED" and body["relaxed"] == ["travel", "years"]


async def test_unknown_names_are_dropped_with_notice(app, client):
    extract = {
        "works": ["존재하지않는작품제목"],
        "genres": ["뮤지컬"],
        "result_type": "LOCATION",
        "out_of_scope": False,
    }
    fake(app, extract=extract)
    body = (await ask(client)).json()
    assert len(body["notices"]) == 2 and body["chips"] == [] and body["status"] == "OK"


async def test_out_of_scope(app, client):
    fake(app, extract={"result_type": "LOCATION", "out_of_scope": True})
    body = (await ask(client, "오늘 날씨 어때")).json()
    assert body["status"] == "OUT_OF_SCOPE" and body["items"] == [] and body["summary"] is None


@pytest.mark.parametrize("mode", ["timeout", "429", "500", "bad_schema"])
async def test_ai_failure_falls_back_with_prefill(app, client, mode):
    fake(app)
    await ask(client)  # 직전 대화
    fake(app, mode=mode)
    res = await ask(client, "그중 바다 보이는 곳")
    body = res.json()
    assert res.status_code == 200 and body["status"] == "FALLBACK"
    assert body["prefill"]["person_ids"] == [1] and body["items"] == []


async def test_work_result_type_and_choice(app, client):
    fake(app, extract={"persons": ["강도윤"], "result_type": "WORK", "out_of_scope": False})
    body = (await ask(client, "강도윤 나온 작품")).json()
    assert {w["title"] for w in body["works"]} == {"부산 추격전", "서면 나이트", "북항 작전"} and body["items"] == []


async def test_filter_panel_search_without_ai(app, client):
    app.state.llm.providers.clear()  # AI가 없어도 동작(FR-410)
    crit = {"person_ids": [1], "base_kind": "any_station", "travel_mode": "walk", "travel_min": 10}
    res = await client.post("/api/search", json={"criteria": crit, "labels": {"person_ids:1": "강도윤"}})
    body = res.json()
    assert res.status_code == 200 and len(body["items"]) == 4 and body["summary"] is None
    assert body["chips"][0] == {"field": "person_ids", "label": "강도윤"}
    station = {"base_kind": "station", "station_id": "119", "travel_mode": "walk", "travel_min": 10}
    names = [i["name"] for i in (await client.post("/api/search", json={"criteria": station})).json()["items"]]
    assert names == ["서면 젊음의거리"]
    bad = await client.post("/api/search", json={"criteria": {"travel_mode": "walk"}})
    assert bad.status_code == 422


async def test_input_rules(client):
    assert (await client.post("/api/query", json={"text": "가" * 201}, headers=H)).status_code == 422
    r = await client.post("/api/query", json={"text": "x"}, headers={"X-Session-Id": SID})
    assert r.status_code == 403
