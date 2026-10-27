"""WP-05: JusoGeocoder(DATA-06). 가이드 테스트 승인키로 받은 실제 응답(fixtures/real/juso/)과 좌표 변환."""

import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import respx

from app.data.adapters.config import load_adapters
from app.data.adapters.errors import ResponseFormatError
from app.data.adapters.juso import JusoCoordClient, JusoGeocoder, JusoSearchClient, clean_keyword, utmk_to_wgs84

REAL = Path(__file__).resolve().parents[1] / "fixtures/real/juso"
CONFS = load_adapters()
SEARCH = f"{CONFS['juso_search'].base_url}/addrLinkApi.do"
COORD = f"{CONFS['juso_coord'].base_url}/addrCoordApi.do"


def real(name: str) -> dict:
    return json.loads((REAL / name).read_text(encoding="utf-8"))


async def no_sleep(_s):
    return None


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as c:
        yield c


def geocoder(http, sido=None) -> JusoGeocoder:
    s = JusoSearchClient(http, "search-key", replace(CONFS["juso_search"]), sleep=no_sleep)
    c = JusoCoordClient(http, "coord-key", replace(CONFS["juso_coord"]), sleep=no_sleep)
    return JusoGeocoder(s, c, sido=sido)


def test_utmk_to_wgs84_known_points():
    # 가이드 예시 좌표(서울 상암동 한국지역정보개발원)와 build-plan 7장의 부산시청 근처 UTM-K 값
    lat, lon = utmk_to_wgs84(945959.0381341814, 1953851.7348996028)
    assert lat == pytest.approx(37.5825, abs=0.001) and lon == pytest.approx(126.8879, abs=0.001)
    lat, lon = utmk_to_wgs84(1143000, 1688000)
    assert lat == pytest.approx(35.177, abs=0.01) and lon == pytest.approx(129.070, abs=0.01)


def test_clean_keyword_drops_parentheses_and_forbidden_chars():
    assert clean_keyword("부산 남구 유엔평화로 63 (대연동, 부산박물관)") == "부산 남구 유엔평화로 63"
    assert clean_keyword("부산 [중구] 광복로 = 1") == "부산 중구 광복로 1"
    assert len(clean_keyword("가" * 60)) == 40
    assert clean_keyword("  (참고)  ") == ""


@respx.mock
async def test_geocode_search_then_coord(http):
    s = respx.get(SEARCH).mock(return_value=httpx.Response(200, json=real("search_test_key.json")))
    c = respx.get(COORD).mock(return_value=httpx.Response(200, json=real("coord_test_key.json")))
    pt = await geocoder(http).geocode("부산 남구 유엔평화로 63 (대연동, 부산박물관)")
    assert pt is not None and pt.source_id == "DATA-06"
    assert pt.lat == pytest.approx(37.5825, abs=0.001) and pt.lon == pytest.approx(126.8879, abs=0.001)
    assert (pt.road_addr, pt.gu) == ("서울특별시 서초구 강남대로12길 6", "서초구")
    sp, cp = s.calls.last.request.url.params, c.calls.last.request.url.params
    assert (sp["confmKey"], sp["keyword"], sp["resultType"]) == ("search-key", "부산 남구 유엔평화로 63", "json")
    # 검색 결과 첫 건의 코드로 좌표를 묻고, 좌표 API는 자기 키를 쓴다
    assert (cp["confmKey"], cp["admCd"], cp["rnMgtSn"], cp["udrtYn"]) == (
        "coord-key",
        "1165010200",
        "116504163008",
        "0",
    )
    assert (cp["buldMnnm"], cp["buldSlno"]) == ("6", "0")


@respx.mock
async def test_geocode_rejects_hits_outside_busan(http):
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json=real("search_test_key.json")))
    coord = respx.get(COORD)
    assert await geocoder(http, sido="부산광역시").geocode("부산 남구 유엔평화로 63") is None
    assert coord.call_count == 0


@respx.mock
async def test_geocode_none_when_no_hit(http):
    empty = {"results": {"common": {"errorCode": "0", "errorMessage": "정상", "totalCount": "0"}, "juso": []}}
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json=empty))
    assert await geocoder(http).geocode("부산 어딘가 없는길 999") is None
    assert await geocoder(http).geocode("(참고만)") is None


@respx.mock
async def test_error_codes_are_format_errors(http):
    respx.get(SEARCH).mock(return_value=httpx.Response(200, json=real("search_e0006.json")))
    respx.get(COORD).mock(return_value=httpx.Response(200, json=real("coord_missing.json")))
    g = geocoder(http)
    with pytest.raises(ResponseFormatError, match="E0006"):
        await g.search.first("부산")
    with pytest.raises(ResponseFormatError, match="E0003"):
        await g.coord.request(g.coord.list_path, {"admCd": "1165010200"})
