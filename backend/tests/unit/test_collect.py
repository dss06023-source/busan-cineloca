"""CollectStep: 부산 원본 2종을 작품·촬영지·촬영 관계로 합친다. 레코드는 손으로 만든 가짜다."""

from datetime import date

import pytest

from app.batch.job import SyncContext
from app.batch.steps import CollectStep, gu_of
from app.data.adapters.busan import FilmLocation


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
