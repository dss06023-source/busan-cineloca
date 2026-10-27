"""API-009~012를 미니 시드 DB와 FakeProvider로 호출한다(시연 장면 4)."""

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.data.ai_gateway.providers import FakeProvider
from app.data.seed import load
from app.main import create_app

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
H = {"X-Session-Id": "6f1c2d1e-8b7a-4c1e-9a52-0d2f3b4c5a6e", "X-Notice-Version": "2026-11-01"}
PREF = {"mood_tags": ["바다"], "start": "서면", "budget_h": 4, "out_of_scope": False}


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


def fake(app, pref=None, intro=None, mode="ok") -> FakeProvider:
    p = FakeProvider(
        {"structure_preference": pref or PREF, "course_intro": intro or {"title": "", "sentences": [], "reasons": []}},
        mode=mode,
    )
    app.state.llm.providers["fake"] = p
    return p


async def test_recommended_list_and_detail(client):
    items = (await client.get("/api/courses")).json()["items"]
    assert [c["id"] for c in items] == [1, 2]  # 승인된 것만
    assert items[0]["stop_count"] == 3 and items[0]["total_min"] == 104
    assert [c["id"] for c in (await client.get("/api/courses?theme=area")).json()["items"]] == [2]
    d = (await client.get("/api/courses/1")).json()
    r = d["route"]
    assert [s["name"] for s in r["stops"]] == ["부산역 광장", "서면 젊음의거리", "자갈치시장"]  # 순서 고정
    assert [leg["mode"] for leg in r["legs"]] == ["walk", "subway", "subway"] and r["legs"][1]["line"] == "1호선"
    assert r["total_min"] == sum(leg["minutes"] for leg in r["legs"]) + 20 * 3
    assert "DATA-08" in r["source_ids"] and r["sources"]
    assert (await client.get("/api/courses/3")).status_code == 404  # 초안


async def test_custom_plan_optimizes_and_fixed_order(client):
    body = {"start": {"station_id": "111"}, "location_ids": [7, 12, 11, 13]}
    r = (await client.post("/api/courses/plan", json=body)).json()
    assert r["start"]["label"] == "남포역" and len(r["stops"]) == 4
    fixed = (await client.post("/api/courses/plan", json={**body, "fixed_order": True})).json()
    assert [s["location_id"] for s in fixed["stops"]] == [7, 12, 11, 13]
    assert r["total_min"] <= fixed["total_min"]
    here = {"start": {"lat": 35.1579, "lon": 129.0594}, "location_ids": [7, 8]}
    assert (await client.post("/api/courses/plan", json=here)).json()["start"]["label"] == "현재 위치"


async def test_custom_plan_rules(client):
    one = await client.post("/api/courses/plan", json={"start": {"station_id": "111"}, "location_ids": [7]})
    assert one.status_code == 422
    no_coords = await client.post("/api/courses/plan", json={"start": {"station_id": "111"}, "location_ids": [7, 21]})
    assert no_coords.status_code == 422 and no_coords.json()["error"]["code"] == "ERR-001"
    two_starts = {"start": {"station_id": "111", "location_id": 7}, "location_ids": [7, 8]}
    assert (await client.post("/api/courses/plan", json=two_starts)).status_code == 422


async def test_ai_course_scene4(app, client):
    """시연 장면 4: 서면 출발 반나절. LLM 2회(구조화·소개), 장소·순서·시간은 시스템이 계산."""
    p = fake(app, intro={"title": "가상 제목 999", "sentences": [], "reasons": []})
    res = await client.post(
        "/api/courses/ai", json={"preference": "서면에서 출발해서 바다 보이는 곳 위주로"}, headers=H
    )
    body = res.json()
    assert res.status_code == 200 and body["status"] == "OK"
    assert body["preference"]["start"] == "서면역" and body["preference"]["budget_h"] == 4
    route = body["route"]
    assert 3 <= len(route["stops"]) <= 8 and route["total_min"] <= 240
    assert len(body["reasons"]) == len(route["stops"])
    assert body["intro"]["ai_generated"] is False and body["intro"]["sentences"]  # 빈 소개 → 템플릿
    assert p.calls == ["structure_preference", "course_intro"]


async def test_ai_course_intro_grounding(app, client):
    first = {"title": "바다 코스", "reasons": [], "sentences": []}
    fake(app, intro=first)
    route = (await client.post("/api/courses/ai", json={"preference": "바다"}, headers=H)).json()["route"]
    name, minutes = route["stops"][0]["name"], route["legs"][0]["minutes"]
    intro = {
        "title": "바다 코스",
        "sentences": [
            {"text": f"{name}에서 시작합니다.", "entities": [name]},
            {"text": "태종대까지 99분 걸립니다.", "entities": []},  # 근거 밖 숫자 → 삭제
        ],
        "reasons": [{"location_id": route["stops"][0]["location_id"], "text": f"{minutes}분이면 닿는 곳"}],
    }
    fake(app, intro=intro)
    body = (await client.post("/api/courses/ai", json={"preference": "바다"}, headers=H)).json()
    assert body["intro"]["ai_generated"] and body["intro"]["sentences"] == [f"{name}에서 시작합니다."]
    assert body["intro"]["dropped_count"] == 1 and body["intro"]["title"] == "바다 코스"
    assert "DATA-11" in body["route"]["source_ids"]


async def test_ai_course_choices_override_text(app, client):
    fake(app)
    body = {"preference": "서면에서 3시간", "start": {"station_id": "203"}, "budget_h": 2}
    r = (await client.post("/api/courses/ai", json=body, headers=H)).json()
    assert r["preference"]["start"] == "해운대역" and r["preference"]["budget_h"] == 2  # FR-308: 선택 항목이 이긴다


@pytest.mark.parametrize("mode", ["timeout", "429", "500", "bad_schema"])
async def test_ai_failure_falls_back_to_manual(app, client, mode):
    fake(app, mode=mode)
    r = (await client.post("/api/courses/ai", json={"preference": "바다"}, headers=H)).json()
    assert r["status"] == "FALLBACK" and r["route"] is None
    manual = {"manual": {"mood_tags": ["바다"]}, "start": {"station_id": "111"}, "budget_h": 4}
    r = (await client.post("/api/courses/ai", json=manual, headers=H)).json()
    assert r["status"] == "OK" and r["intro"]["ai_generated"] is False  # 소개도 장애 → 템플릿(FR-312)


async def test_infeasible_budget_and_input_rules(app, client):
    fake(app)
    r = (await client.post("/api/courses/ai", json={"manual": {}, "start": {"station_id": "119"}, "budget_h": 1},
                           headers=H)).json()  # fmt: skip
    assert r["status"] == "INFEASIBLE" and r["reason"] == "budget"  # 3곳 체류만 60분
    both = await client.post("/api/courses/ai", json={"preference": "a", "manual": {}}, headers=H)
    assert both.status_code == 422
    assert (await client.post("/api/courses/ai", json={"preference": "가" * 201}, headers=H)).status_code == 422
    out = fake(app, pref={"out_of_scope": True})
    r = (await client.post("/api/courses/ai", json={"preference": "주식 추천"}, headers=H)).json()
    assert r["status"] == "OUT_OF_SCOPE" and out.calls == ["structure_preference"]
