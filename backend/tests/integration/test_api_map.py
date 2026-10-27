"""API-005·006·007을 미니 시드 DB에서 호출한다."""

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.data.seed import load
from app.main import create_app

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "infra/seed/mini_seed.sql"
SEOMYEON = {"lat": 35.1579, "lon": 129.0594}


@pytest.fixture
async def client(fresh_db, tmp_path):
    load(fresh_db, MINI_SEED)
    app = create_app(Settings(database_url=fresh_db, log_dir=str(tmp_path)))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        yield c


async def search(client, **body):
    return await client.post("/api/locations/search", json=body)


async def test_radius_options(client):
    names = {}
    for r in (500, 1000, 3000):
        res = await search(client, base=SEOMYEON, radius_m=r)
        assert res.status_code == 200
        names[r] = [i["name"] for i in res.json()["items"]]
    assert names[500] == ["서면 젊음의거리"]
    assert names[1000] == ["서면 젊음의거리"]
    assert names[3000] == ["서면 젊음의거리", "부산시민공원"]


async def test_item_card_fields_and_sources(client):
    body = (await search(client, base={"station_id": "203"}, radius_m=1000)).json()
    first = body["items"][0]
    assert first["name"] == "해운대해수욕장" and first["distance_m"] < 1000
    assert len(first["works"]) <= 3 and first["work_count"] == 2
    assert first["works"][0]["title"] == "해운대 스캔들"  # 최신작 먼저
    assert first["station"]["id"] == "203"
    assert body["source_ids"] == ["DATA-06", "DATA-08", "DEV-SEED"]
    assert [s["id"] for s in body["sources"]] == body["source_ids"]


async def test_filters_all_must_match(client):
    base = {"station_id": "111"}
    everything = (await search(client, base=base, radius_m=3000)).json()["items"]
    dramas = (await search(client, base=base, radius_m=3000, filters={"genres": ["드라마"]})).json()["items"]
    old_dramas = (
        await search(client, base=base, radius_m=3000, filters={"genres": ["드라마"], "year_to": 2005})
    ).json()["items"]
    assert len(everything) > len(dramas) > len(old_dramas) > 0
    assert {i["name"] for i in old_dramas} == {"국제시장", "자갈치시장", "BIFF광장"}
    yeongdo = (await search(client, base=base, radius_m=3000, filters={"gus": ["영도구"]})).json()["items"]
    assert {i["name"] for i in yeongdo} == {"영도대교", "흰여울문화마을"}


async def test_gu_base_lists_whole_district(client):
    items = (await search(client, base={"gu": "중구"}, radius_m=1000)).json()["items"]
    # 중구 5곳 중 촬영 기록이 있는 4곳(용두산공원은 미니 시드에 작품이 없음)
    assert len(items) == 4 and all(i["distance_m"] is None for i in items)


@pytest.mark.parametrize(
    "body",
    [
        {"base": {"lat": 37.5665, "lon": 126.978}},  # 서울
        {"base": SEOMYEON, "radius_m": 2000},
        {"base": {"station_id": "999"}},
        {"base": {"gu": "강남구"}},
        {"base": {**SEOMYEON, "gu": "중구"}},
        {"base": {"lat": 35.1}},
        {"base": SEOMYEON, "filters": {"gus": ["강남구"]}},
    ],
)
async def test_invalid_input_is_err001(client, body):
    res = await client.post("/api/locations/search", json=body)
    assert res.status_code == 422 and res.json()["error"]["code"] == "ERR-001"


async def test_location_detail(client):
    d = (await client.get("/api/locations/12")).json()
    assert d["location"]["name"] == "자갈치시장"
    assert d["station"]["id"] == "110" and d["walk_min"] == 3
    assert d["certifiable"] is True and d["cert_block_reason"] is None
    assert d["tags"] == ["시장", "바다"]
    assert {w["title"] for w in d["works"]} == {"남포동 블루스", "부산 추격전"}
    assert d["source_ids"] == ["DATA-06", "DATA-08", "DEV-SEED"]


async def test_location_without_coords_not_certifiable(client):
    d = (await client.get("/api/locations/21")).json()
    assert d["location"]["lat"] is None and d["certifiable"] is False and d["cert_block_reason"] == "no_coords"
    assert "DATA-06" not in d["source_ids"]


async def test_location_not_found(client):
    res = await client.get("/api/locations/999")
    assert res.status_code == 404 and res.json()["error"]["code"] == "HTTP-404"


async def test_meta(client):
    m = (await client.get("/api/meta")).json()
    assert len(m["districts"]) == 16 and m["default_station_id"] == "113"
    assert len(m["stations"]) == 12 and "드라마" in m["genres"]
    assert m["year_range"] == [2001, 2022]


async def test_sources_ledger(client):
    body = (await client.get("/api/sources")).json()
    assert [s["id"] for s in body["sources"]][:2] == ["DATA-01", "DATA-02"]
    assert len(body["sources"]) == 13 and len(body["licenses"]) == 13
    assert "통합전산망" in body["kobis_notice"]
