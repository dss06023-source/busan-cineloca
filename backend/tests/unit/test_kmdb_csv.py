"""WP-05: KMDb 영화기본정보 CSV 어댑터. 원본 대신 같은 형식(CP949, 헤더 25칸·행 26칸)의 손으로 만든 가짜를 쓴다."""

import csv
from pathlib import Path

import pytest

from app.data.adapters.errors import AdapterError, ResponseFormatError
from app.data.adapters.kmdb_csv import COLUMNS, KmdbCsvCatalog, parse_row, read_csv, stored_kmdb
from app.data.adapters.policy import PolicyGuard
from app.services.archive.service import info_from_stored

FAKE = Path(__file__).resolve().parents[1] / "fixtures/fake/kmdb_basic.csv"


def first_rows() -> dict:
    out: dict = {}
    for m in read_csv(FAKE):
        out.setdefault(m.kmdb_id, m)
    return out


@pytest.fixture(scope="module")
def catalog() -> KmdbCsvCatalog:
    return KmdbCsvCatalog.load(FAKE)


def test_reads_by_position_not_header_names():
    movies = first_rows()
    m = movies["K90002"]
    assert (m.title, m.title_en, m.title_org, m.kind, m.prdt_year) == (
        "가짜 부산 이야기",
        "Fake Busan Story",
        None,
        "극영화",
        2016,
    )
    assert m.genres == ("액션", "스릴러") and m.nations == ("대한민국",)
    assert m.directors == ("김가짜",)
    # 헤더 이름대로 읽으면 '출연' 자리에 각본이 온다. 위치로 읽고 배역 괄호는 뺀다
    assert m.actors == ("최가짜", "박가짜", "이가짜")
    assert m.keywords == ("부산", "기차", "추격") and m.release_date == "20160720"
    assert m.link == "https://www.kmdb.or.kr/db/kor/detail/movie/K/90002"


def test_null_literals_and_line_breaks():
    movies = first_rows()
    sparse = movies["K90003"]
    assert sparse.title_en is None and sparse.plot is None and sparse.keywords == ()
    assert movies["F90001"].plot == "가짜 줄거리 첫 줄\n둘째 줄"
    assert movies["F90001"].nations == ("미국", "프랑스")
    assert movies["K90004"].link == "https://example.invalid/kmdb/K90004"  # KMDBURL이 있으면 그 값


def test_duplicate_id_keeps_first_row(catalog):
    assert len(catalog) == 4
    assert catalog.by_id["K90002"].title == "가짜 부산 이야기"


def test_wrong_header_or_row_width_is_format_error(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("id,title\nK1,x\n", encoding="cp949")
    with pytest.raises(ResponseFormatError, match="header"):
        list(read_csv(bad))
    with pytest.raises(ResponseFormatError, match="25 columns"):
        parse_row(["x"] * 25)
    assert len(COLUMNS) == 26


def test_candidates_exact_title_then_closest_year(catalog):
    ids = [m.kmdb_id for m in catalog.candidates("가짜 부산 이야기", 2016)]
    assert ids == ["K90002", "K90004", "K90003"]  # 같은 제목 2편(연도 가까운 순) → 앞부분이 같은 속편
    assert [m.kmdb_id for m in catalog.candidates("가짜부산이야기", 1990, limit=1)] == ["K90004"]


def test_candidates_prefix_and_english_title(catalog):
    assert [m.kmdb_id for m in catalog.candidates("가짜 부산 이야기 2", 2019)][0] == "K90003"
    assert [m.kmdb_id for m in catalog.candidates("FAKE SEA STORY")] == ["F90001"]
    assert catalog.candidates("없는 영화") == [] and catalog.candidates("  ") == []


async def test_detail_as_movie_info_provider(catalog):
    info = await catalog.detail("K90002")
    assert info.source_id == "DATA-04" and info.plot == "부산에서 벌어지는 가짜 이야기"
    assert info.keywords == ["부산", "기차", "추격"] and info.posters == []
    with pytest.raises(AdapterError):
        await catalog.detail("K00000")


def test_policy_id_only_keeps_kmdb_id_and_store_keeps_all(catalog):
    m = catalog.by_id["K90002"]
    assert PolicyGuard({"DATA-04": "ID_ONLY"}).storable("DATA-04", m) == {"kmdb_id": "K90002"}
    stored = PolicyGuard({"DATA-04": "STORE"}).storable("DATA-04", m)
    assert stored["plot"] and stored["actors"] == ("최가짜", "박가짜", "이가짜")


def test_fixture_is_cp949_with_25_column_header():
    with open(FAKE, encoding="cp949", newline="") as f:
        rows = list(csv.reader(f))
    assert len(rows[0]) == 25 and all(len(r) == 26 for r in rows[1:])


def test_stored_kmdb_round_trips_to_movie_info(catalog):
    m = catalog.by_id["K90002"]
    info = info_from_stored(stored_kmdb(m))
    assert info.source_id == "DATA-04" and info.plot == m.plot and info.link == m.link
    assert info.keywords == list(m.keywords) and info.posters == []
