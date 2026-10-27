"""CollectStep·GeocodeStep: 부산 원본 2종을 합치고 주소에 좌표를 채운다. 레코드와 좌표는 손으로 만든 가짜다."""

from datetime import date

import pytest

from app.batch.job import SyncContext
from app.batch.steps import CollectStep, GeocodeStep, gu_of
from app.data.adapters.busan import FilmLocation
from app.data.adapters.errors import AdapterTimeout, QuotaExhausted
from app.data.adapters.juso import GeoPoint
from app.data.models import StagedLocation


class Src:
    def __init__(self, source_id, records):
        self.source_id, self.records = source_id, records

    async def fetch_all(self):
        return self.records


async def collect(*sources):
    ctx = SyncContext()
    await CollectStep(list(sources), today=lambda: date(2026, 10, 27)).run(ctx)
    return ctx


@pytest.mark.parametrize(
    ("address", "gu"),
    [
        ("부산 동구 초량동 1206-1 동구 중앙대로 200", "동구"),
        ("부산광역시 부산진구 전포대로 1", "부산진구"),
        ("부산 기장군 기장읍", "기장군"),
        ("부산 해운대구 우동", "해운대구"),
        ("서울 종로구 세종대로", None),
        (None, None),
    ],
)
def test_gu_of(address, gu):
    assert gu_of(address) == gu


async def test_merges_same_work_and_place_across_sources():
    ctx = await collect(
        Src("DATA-01", [FilmLocation("DATA-01", "부산 행", "자갈치 시장", release_date="2016-07-20")]),
        Src("DATA-02", [FilmLocation("DATA-02", "부산행", "자갈치시장", address="부산 중구 자갈치해안로 52")]),
    )
    assert [(w.ext_key, w.title, w.release_year, w.source_id) for w in ctx.works] == [
        ("t:부산행", "부산 행", 2016, "DATA-01")
    ]
    # 주소 없는 DATA-01 장소가 같은 이름의 씨네맵 주소로 같은 촬영지가 된다
    assert [(x.ext_key, x.gu, x.address) for x in ctx.locations] == [
        ("자갈치시장|중구", "중구", "부산 중구 자갈치해안로 52")
    ]
    assert sorted((s.work_key, s.location_key, s.source_id) for s in ctx.shootings) == [
        ("t:부산행", "자갈치시장|중구", "DATA-01"),
        ("t:부산행", "자갈치시장|중구", "DATA-02"),
    ]
    assert ctx.shootings[0].base_date == date(2026, 10, 27)


async def test_ambiguous_place_name_is_not_guessed():
    ctx = await collect(
        Src("DATA-01", [FilmLocation("DATA-01", "친구", "시장")]),
        Src("DATA-02", [
            FilmLocation("DATA-02", "A", "시장", address="부산 중구 1"),
            FilmLocation("DATA-02", "B", "시장", address="부산 동구 2"),
        ]),
    )  # fmt: skip
    assert {x.ext_key for x in ctx.locations} == {"시장|", "시장|중구", "시장|동구"}


async def test_year_filled_from_later_record_and_duplicates_dropped():
    rec = FilmLocation("DATA-01", "해운대", "미포", release_date="2009-07-22")
    ctx = await collect(Src("DATA-02", [FilmLocation("DATA-02", "해운대", "미포")]), Src("DATA-01", [rec, rec]))
    assert ctx.works[0].release_year == 2009 and ctx.works[0].source_id == "DATA-02"
    assert len(ctx.shootings) == 2


async def test_empty_title_or_place_recorded_as_failure_without_values():
    ctx = await collect(Src("DATA-01", [FilmLocation("DATA-01", " ", "장소"), FilmLocation("DATA-01", "작품", "!!")]))
    assert (
        ctx.works == []
        and ctx.failures == [{"step": "collect", "error": "empty_title_or_place", "source": "DATA-01"}] * 2
    )


async def test_build_steps_follows_keys():
    from app.batch.__main__ import build_steps
    from app.config import Settings

    assert await build_steps(Settings(data_go_kr_key="", kmdb_csv_path=""), None, None) == []
    steps = await build_steps(Settings(data_go_kr_key="k", kmdb_csv_path=""), None, None)
    assert [s.name for s in steps] == ["collect"]
    assert [src.source_id for src in steps[0].sources] == ["DATA-01", "DATA-02"]


class FakeGeocoder:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    async def geocode(self, address):
        self.calls.append(address)
        a = self.answers.get(address)
        if isinstance(a, Exception):
            raise a
        return a


def loc(key, address, gu=None, **kw):
    return StagedLocation(key, key, key, address, gu, **kw)


async def geocode(locations, answers, known=None):
    async def known_fn():
        return known or {}

    g = FakeGeocoder(answers)
    ctx = SyncContext(locations=locations)
    await GeocodeStep(g, known_fn).run(ctx)
    return {x.ext_key: x for x in ctx.locations}, ctx.failures, g.calls


async def test_geocode_fills_coordinates_and_marks_failures():
    out, failures, calls = await geocode(
        [loc("a", "부산 중구 1", "중구"), loc("b", "부산 어딘가"), loc("c", None), loc("d", "부산 동구 2")],
        {"부산 중구 1": GeoPoint(35.1, 129.0, "도로명", "중구"), "부산 동구 2": AdapterTimeout("t")},
    )
    assert (out["a"].lat, out["a"].lon, out["a"].geocode_status) == (35.1, 129.0, "ok")
    assert out["b"].geocode_status == "failed" and out["b"].lat is None
    assert out["c"].geocode_status == "failed" and "c" not in calls  # 주소 없는 곳은 부르지 않음
    assert out["d"].geocode_status == "failed"
    assert failures == [{"step": "geocode", "error": "AdapterTimeout", "count": 1}]  # 주소는 남기지 않음


async def test_geocode_fills_missing_gu_but_keeps_parsed_one():
    out, _, _ = await geocode(
        [loc("a", "주소A"), loc("b", "주소B", "남구")],
        {"주소A": GeoPoint(35.0, 129.0, "r", "해운대구"), "주소B": GeoPoint(35.0, 129.0, "r", "수영구")},
    )
    assert (out["a"].gu, out["b"].gu) == ("해운대구", "남구")


async def test_geocode_reuses_previous_result_for_same_address():
    out, _, calls = await geocode(
        [loc("a", "같은 주소"), loc("b", "바뀐 주소")],
        {"바뀐 주소": GeoPoint(35.2, 129.2, "r", "북구")},
        known={"a": ("같은 주소", 35.5, 129.5), "b": ("예전 주소", 1.0, 1.0)},
    )
    assert calls == ["바뀐 주소"]
    assert (out["a"].lat, out["a"].geocode_status) == (35.5, "ok") and out["b"].lat == 35.2


async def test_geocode_stops_calling_after_quota():
    out, failures, calls = await geocode(
        [loc("a", "A"), loc("b", "B"), loc("c", "C")],
        {"A": QuotaExhausted("q"), "B": GeoPoint(35.0, 129.0, "r", "중구")},
    )
    assert calls == ["A"] and {x.geocode_status for x in out.values()} == {"failed"}
    assert failures == [{"step": "geocode", "error": "QuotaExhausted", "count": 1}]


async def test_build_steps_adds_geocode_only_with_both_juso_keys():
    from app.batch.__main__ import build_steps
    from app.config import Settings

    base = {"data_go_kr_key": "", "kmdb_csv_path": ""}
    assert await build_steps(Settings(**base, juso_key="k", juso_coord_key=""), None, None) == []
    steps = await build_steps(Settings(**base, juso_key="k", juso_coord_key="c"), None, None)
    assert [s.name for s in steps] == ["geocode"]
