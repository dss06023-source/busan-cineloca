"""WP-05: TourPhotoClient(TourAPI KorService2). 2026-10-27 실제 응답 사본(fixtures/real/tourapi/)으로 확인."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import respx

from app.data.adapters.config import load_adapters
from app.data.adapters.data_go_kr import body_items
from app.data.adapters.errors import AdapterError, ResponseFormatError
from app.data.adapters.policy import PolicyGuard
from app.data.adapters.tour import TourPhotoClient

REAL = Path(__file__).resolve().parents[1] / "fixtures/real/tourapi"
CONF = load_adapters()["tourapi"]
URL = f"{CONF.base_url}/locationBasedList2"
KEY = "test-key-not-real"


def real(name: str) -> dict:
    return json.loads((REAL / name).read_text(encoding="utf-8"))


def pages() -> list[httpx.Response]:
    return [httpx.Response(200, json=real("location_p1.json")), httpx.Response(200, json=real("location_p2.json"))]


async def no_sleep(_s):
    return None


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as c:
        yield c


def client(http, **conf) -> TourPhotoClient:
    return TourPhotoClient(http, KEY, replace(CONF, **conf), sleep=no_sleep)


@respx.mock
async def test_near_reads_all_pages_of_real_response(http):
    route = respx.get(URL).mock(
        side_effect=[
            httpx.Response(200, json=real("location_p1.json")),
            httpx.Response(200, json=real("location_p2.json")),
        ]
    )
    places = await client(http, page_size=3).near(35.1587, 129.1604, radius_m=2000)
    assert len(places) == 5
    first = places[0]
    assert (first.content_id, first.title, first.kogl_type) == ("127004", "해운대 관광특구", 3)
    assert first.lat == pytest.approx(35.1584383046) and first.lon == pytest.approx(129.1598690678)
    assert first.dist_m == pytest.approx(55.42, abs=0.01)
    p = route.calls[0].request.url.params
    assert (p["serviceKey"], p["_type"], p["MobileOS"], p["arrange"], p["contentTypeId"]) == (
        KEY,
        "json",
        "ETC",
        "E",
        "12",
    )
    assert (p["mapX"], p["mapY"], p["radius"]) == ("129.1604000", "35.1587000", "2000")
    assert route.calls[1].request.url.params["pageNo"] == "2"


@respx.mock
async def test_photos_near_keeps_kogl_type1_only(http):
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(200, json=real("location_p1.json")),
            httpx.Response(200, json=real("location_p2.json")),
        ]
    )
    photos = await client(http, page_size=3).photos_near(35.1587, 129.1604, radius_m=2000)
    assert [p.title for p in photos] == ["동백공원", "부산 영화의 거리", "마린시티"]
    assert all(p.image_url.startswith("http") for p in photos)


@respx.mock
async def test_empty_result_items_is_empty_string(http):
    respx.get(URL).mock(return_value=httpx.Response(200, json=real("location_empty.json")))
    assert await client(http).near(34.5, 129.0, radius_m=100) == []


def test_single_item_object_is_list():
    payload = real("location_p2.json")
    one = payload["response"]["body"]["items"]["item"][0]
    payload["response"]["body"]["items"]["item"] = one
    assert body_items(payload)[0] == [one]


@respx.mock
async def test_bad_key_gateway_error_is_not_retried(http):
    route = respx.get(URL).mock(return_value=httpx.Response(403, json=real("bad_key.json")))
    with pytest.raises(ResponseFormatError, match="gateway error 30"):
        await client(http).near(35.1, 129.0)
    assert route.call_count == 1


@respx.mock
async def test_result_code_error_and_server_error(http):
    bad = {"response": {"header": {"resultCode": "10", "resultMsg": "INVALID_REQUEST_PARAMETER_ERROR"}}}
    route = respx.get(URL).mock(side_effect=[httpx.Response(200, json=bad), *[httpx.Response(502)] * 3])
    c = client(http)
    with pytest.raises(ResponseFormatError, match="resultCode 10"):
        await c.near(35.1, 129.0)
    with pytest.raises(AdapterError, match="http 502"):
        await c.near(35.1, 129.0)
    assert route.call_count == 4


def test_parsed_place_passes_store_policy():
    places, _ = TourPhotoClient.parse(None, real("location_p1.json"))  # parse는 인스턴스 상태를 쓰지 않는다
    row = PolicyGuard({"DATA-10": "STORE"}).storable("DATA-10", places[0])
    assert row["content_id"] == "127004" and row["kogl_type"] == 3


def test_real_fixtures_hold_no_service_key():
    for f in REAL.glob("*.json"):
        text = f.read_text(encoding="utf-8")
        assert "serviceKey" not in text, f
