"""WP-05: BaseApiClient(재시도 3회, 하루 한도 80%, 형식 검사), KobisClient, PolicyGuard. 실제 API는 부르지 않는다."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

from app.data.adapters.config import load_adapters
from app.data.adapters.errors import AdapterError, AdapterTimeout, QuotaExhausted, ResponseFormatError
from app.data.adapters.kobis import KobisClient, KobisMovie
from app.data.adapters.policy import PolicyGuard, PolicyViolation
from app.data.models import Source

FAKE = Path(__file__).resolve().parents[1] / "fixtures/fake/kobis"
CONF = load_adapters()["kobis"]
LIST = f"{CONF.base_url}/searchMovieList.json"
INFO = f"{CONF.base_url}/searchMovieInfo.json"
KEY = "test-key-not-real"


def fake(name: str) -> dict:
    return json.loads((FAKE / name).read_text(encoding="utf-8"))


class MemUsage:
    def __init__(self, start: int = 0):
        self.d: dict = {}
        self.start = start

    async def incr(self, day, key, by=1):
        self.d[(day, key)] = self.d.get((day, key), self.start) + by
        return self.d[(day, key)]

    async def get(self, day, key):
        return self.d.get((day, key), self.start)


async def no_sleep(_s: float) -> None:
    return None


@pytest.fixture
async def http():
    async with httpx.AsyncClient() as c:
        yield c


def client(http, usage=None, **conf) -> KobisClient:
    return KobisClient(http, KEY, replace(CONF, **conf), usage=usage, today=lambda: date(2026, 10, 27), sleep=no_sleep)


@respx.mock
async def test_fetch_all_pages_until_total(http):
    route = respx.get(LIST).mock(
        side_effect=[
            httpx.Response(200, json=fake("movie_list_p1.json")),
            httpx.Response(200, json=fake("movie_list_p2.json")),
        ]
    )
    usage = MemUsage()
    movies = await client(http, usage, page_size=2).search("가짜 부산")
    assert [m.movie_cd for m in movies] == ["20990001", "20990002", "20990003"]
    assert movies[0] == KobisMovie("20990001", "가짜 부산 이야기", "FAKE BUSAN STORY", 2019, "20200115", ("김가짜",))
    assert movies[1].open_dt is None and movies[2].prdt_year is None
    assert movies[2].directors == ("박가짜", "이가짜")
    # 페이지 매개변수와 키가 들어가고, 호출 수가 하루 사용량에 쌓인다
    p1, p2 = (c.request.url.params for c in route.calls)
    assert (p1["curPage"], p1["itemPerPage"], p1["movieNm"], p1["key"]) == ("1", "2", "가짜 부산", KEY)
    assert p2["curPage"] == "2"
    assert usage.d == {(date(2026, 10, 27), "api:kobis"): 2}


@respx.mock
async def test_retries_three_times_on_5xx_then_succeeds(http):
    route = respx.get(LIST).mock(
        side_effect=[httpx.Response(500), httpx.ConnectError("x"), httpx.Response(200, json=fake("movie_list_p2.json"))]
    )
    slept: list[float] = []

    async def sleep(s):
        slept.append(s)

    c = KobisClient(http, KEY, CONF, sleep=sleep)
    assert len(await c.search("x", max_items=10)) == 1
    assert route.call_count == 3
    assert slept == [CONF.backoff_s, CONF.backoff_s * 2]


@respx.mock
async def test_gives_up_after_three_attempts(http):
    route = respx.get(LIST).mock(return_value=httpx.Response(503))
    with pytest.raises(AdapterError, match="http 503"):
        await client(http).search("x")
    assert route.call_count == 3


@respx.mock
async def test_timeout_is_retried_and_reported(http):
    route = respx.get(LIST).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(AdapterTimeout):
        await client(http).search("x")
    assert route.call_count == 3


@respx.mock
async def test_4xx_is_not_retried(http):
    route = respx.get(LIST).mock(return_value=httpx.Response(401))
    with pytest.raises(AdapterError, match="http 401"):
        await client(http).search("x")
    assert route.call_count == 1


@respx.mock
async def test_error_message_never_contains_key(http):
    respx.get(LIST).mock(side_effect=httpx.ConnectError(f"failed {LIST}?key={KEY}"))
    with pytest.raises(AdapterError) as e:
        await client(http).search("x")
    assert KEY not in str(e.value) and e.value.__cause__ is None


@respx.mock
async def test_fault_info_is_format_error(http):
    route = respx.get(LIST).mock(return_value=httpx.Response(200, json=fake("fault.json")))
    with pytest.raises(ResponseFormatError, match="320010"):
        await client(http).search("x")
    assert route.call_count == 1  # 기관 오류는 다시 보내도 같다


@respx.mock
async def test_unexpected_shape_and_non_json(http):
    respx.get(LIST).mock(
        side_effect=[
            httpx.Response(200, json={"movieListResult": {"movieList": [{}]}}),
            httpx.Response(200, text="<html>"),
        ]
    )
    c = client(http)
    with pytest.raises(ResponseFormatError):
        await c.search("x")
    with pytest.raises(ResponseFormatError, match="not json"):
        await c.search("x")


@respx.mock
async def test_daily_quota_stops_at_80_percent(http):
    route = respx.get(LIST).mock(return_value=httpx.Response(200, json=fake("movie_list_p2.json")))
    assert CONF.quota == int(CONF.daily_limit * 0.8)
    under = MemUsage(start=CONF.quota - 1)
    await client(http, under).search("x", max_items=10)  # 한도 바로 아래면 부른다
    with pytest.raises(QuotaExhausted):
        await client(http, under).search("x", max_items=10)  # 방금 한 번으로 80%에 닿았다
    assert route.call_count == 1


@respx.mock
async def test_rating_uses_last_audit_with_single_attempt(http):
    route = respx.get(INFO).mock(return_value=httpx.Response(200, json=fake("movie_info.json")))
    assert await client(http).rating("20990001", timeout_s=3.0) == "12세이상관람가"
    assert route.calls.last.request.url.params["movieCd"] == "20990001"


@respx.mock
async def test_rating_none_for_unknown_or_unrated(http):
    no_audit = fake("movie_info.json")
    no_audit["movieInfoResult"]["movieInfo"]["audits"] = []
    respx.get(INFO).mock(
        side_effect=[httpx.Response(200, json=fake("movie_info_empty.json")), httpx.Response(200, json=no_audit)]
    )
    c = client(http)
    assert await c.rating("00000000", timeout_s=3.0) is None
    assert await c.rating("20990001", timeout_s=3.0) is None


@respx.mock
async def test_rating_does_not_retry_so_detail_is_not_blocked(http):
    route = respx.get(INFO).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(AdapterTimeout):
        await client(http).rating("20990001", timeout_s=3.0)
    assert route.call_count == 1


def test_adapter_errors_are_provider_errors():
    """ArchiveService는 ProviderError를 잡아 등급을 null로 강등한다(ERR-006)."""
    from app.data.ai_gateway.errors import ProviderError

    assert issubclass(QuotaExhausted, ProviderError) and issubclass(ResponseFormatError, ProviderError)


# PolicyGuard(FR-703, BR-01)

SOURCES = [
    Source("DATA-01", "부산광역시", "영화 속 부산정보", "u", "l", "STORE"),
    Source("DATA-05", "영화진흥위원회", "KOBIS", "u", "l", "ID_ONLY"),
    Source("DATA-07", "카카오", "지도", "u", "l", "NO_STORE"),
    Source("DATA-99", "가짜", "식별자 미정", "u", "l", "ID_ONLY"),
]
MOVIE = KobisMovie("20990001", "가짜 부산 이야기", "", 2019, None, ("김가짜",))


def test_policy_store_passes_record_unchanged():
    g = PolicyGuard.from_sources(SOURCES)
    assert g.storable("DATA-01", {"ext_key": "a", "name": "광안리"}) == {"ext_key": "a", "name": "광안리"}


def test_policy_id_only_keeps_identifier_only():
    g = PolicyGuard.from_sources(SOURCES)
    assert g.storable("DATA-05", MOVIE) == {"movie_cd": "20990001"}
    assert g.storable_all("DATA-05", [MOVIE, replace(MOVIE, movie_cd="20990002")]) == [
        {"movie_cd": "20990001"},
        {"movie_cd": "20990002"},
    ]


def test_policy_no_store_and_unknown_source_drop_everything():
    g = PolicyGuard.from_sources(SOURCES)
    assert g.storable("DATA-07", {"lat": 35.1, "lon": 129.0}) is None
    assert g.storable("DATA-42", {"x": 1}) is None
    assert g.storable_all("DATA-07", [{"a": 1}, {"b": 2}]) == []


def test_policy_id_only_without_declared_fields_fails_loudly():
    with pytest.raises(PolicyViolation):
        PolicyGuard.from_sources(SOURCES).storable("DATA-99", {"id": 1})


def test_real_fixtures_hold_no_kobis_payload():
    """KOBIS 응답 본문은 저장 금지: 실제 응답 사본 폴더에 KOBIS 모양이 없어야 한다(NFR-007)."""
    real = Path(__file__).resolve().parents[1] / "fixtures/real"
    for f in real.rglob("*"):
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")
            assert "movieListResult" not in text and "movieInfoResult" not in text, f
