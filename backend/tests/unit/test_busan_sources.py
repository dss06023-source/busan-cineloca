"""WP-05: 부산 원본 3종(영화 속 부산정보·씨네맵·역사정보). 2026-10-27 실제 응답 사본(fixtures/real/)으로 확인."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import respx

from app.data.adapters.busan import CineMapClient, FilmLocation, FilmLocationClient, StationClient, StationRecord
from app.data.adapters.config import load_adapters
from app.data.adapters.errors import ResponseFormatError
from app.data.adapters.policy import PolicyGuard

REAL = Path(__file__).resolve().parents[1] / "fixtures/real"
CONFS = load_adapters()
KEY = "test-key-not-real"


def real(path: str) -> dict:
    return json.loads((REAL / path).read_text(encoding="utf-8"))


def ok(path: str) -> httpx.Response:
    return httpx.Response(200, json=real(path))


async def no_sleep(_s):
    return None


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as c:
        yield c


def make(cls, http, **conf):
    return cls(http, KEY, replace(CONFS[cls.name], **conf), sleep=no_sleep)


@respx.mock
async def test_film_location_pages_and_fields(http):
    url = f"{CONFS['bfc_movie'].base_url}/getBfcMovieBusan"
    # 실제 totalCount는 2066이라 3번째 페이지(빈 목록)에서 멈추는지 본다
    route = respx.get(url).mock(
        side_effect=[ok("bfc_movie/p1.json"), ok("bfc_movie/p2.json"), ok("bfc_movie/beyond.json")]
    )
    rows = await make(FilmLocationClient, http, page_size=3).fetch_all()
    assert len(rows) == 6 and route.call_count == 3
    assert rows[0] == FilmLocation("DATA-01", "검은 수녀들", "동아대학교 부민캠퍼스", None, "2025-01-24")
    assert rows[3].place_name == "부산천(동구 충장대로 255)"
    p = route.calls[0].request.url.params
    assert (p["serviceKey"], p["resultType"], p["pageNo"], p["numOfRows"]) == (KEY, "json", "1", "3")
    assert "_type" not in p


@respx.mock
async def test_cinemap_has_address(http):
    respx.get(f"{CONFS['cinemap'].base_url}/getCineMap").mock(return_value=ok("cinemap/p1.json"))
    rows, total = make(CineMapClient, http).parse(real("cinemap/p1.json"))
    assert total == 2193
    assert rows[0].source_id == "DATA-02" and rows[0].work_title == "넷플릭스 굿뉴스"
    assert rows[1].address == "부산 남구 유엔평화로 63 (대연동, 부산박물관)"
    assert rows[0].release_date is None


@respx.mock
async def test_station_header_without_response_wrapper(http):
    url = f"{CONFS['station'].base_url}/getStationInfo"
    route = respx.get(url).mock(side_effect=[ok("station/p1.json"), ok("station/beyond.json")])
    rows = await make(StationClient, http, page_size=3).fetch_all()
    assert rows[0] == StationRecord("100", "동매", "부산광역시 사하구 신산로 지하168 (신평동)", "051-678-6100")
    assert len(rows) == 3 and route.call_count == 2
    assert route.calls[0].request.url.params["_type"] == "json"


@respx.mock
async def test_bad_key_and_result_code(http):
    url = f"{CONFS['bfc_movie'].base_url}/getBfcMovieBusan"
    bad = {"response": {"header": {"resultCode": "03", "resultMsg": "NODATA_ERROR"}}}
    respx.get(url).mock(
        side_effect=[httpx.Response(403, json=real("bfc_movie/bad_key.json")), httpx.Response(200, json=bad)]
    )
    c = make(FilmLocationClient, http)
    with pytest.raises(ResponseFormatError, match="gateway error 30"):
        await c.fetch_all()
    with pytest.raises(ResponseFormatError, match="resultCode 03"):
        await c.fetch_all()


def test_missing_field_is_format_error(http):
    payload = real("cinemap/p1.json")
    del payload["response"]["body"]["items"]["item"][0]["opusNm"]
    with pytest.raises(ResponseFormatError):
        CineMapClient.parse(make(CineMapClient, http), payload)


def test_store_policy_passes_film_locations(http):
    rows, _ = make(FilmLocationClient, http).parse(real("bfc_movie/p1.json"))
    g = PolicyGuard({"DATA-01": "STORE"})
    assert g.storable_all("DATA-01", rows)[0]["work_title"] == "검은 수녀들"
