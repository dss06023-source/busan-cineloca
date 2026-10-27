"""스포일러 단계별 근거 묶음(FR-109, AI-REQ-07)."""

from app.data.models import MovieInfo, Person, Work, WorkDetail, WorkLocation
from app.services.archive.service import EVIDENCE, info_from_stored

DETAIL = WorkDetail(
    work=Work(id=1, title="가상 영화", release_year=2019, genres=["드라마"], source_id="DEV-SEED"),
    people=[Person(1, "가상 감독", "director", 1), Person(2, "가상 배우", "actor", 1)],
    locations=[WorkLocation(4, "가상 부두", "영도구", 35.0, 129.0, "DATA-01")],
    source_ids=["DEV-SEED", "DATA-01"],
)
INFO = MovieInfo(source_id="DATA-04", plot="부두에서 일어난 사건", keywords=["부두"])


def test_none_level_has_no_plot():
    ev = EVIDENCE["none"].build(DETAIL, INFO)
    assert "plot" not in ev.bundle["work"] and "부두에서 일어난 사건" not in str(ev.bundle)
    assert ev.bundle["work"]["directors"] == ["가상 감독"] and ev.bundle["work"]["actors"] == ["가상 배우"]
    assert ev.bundle["work"]["keywords"] == ["부두"] and ev.bundle["spoiler"] == "none"
    assert ev.bundle["locations"] == [{"id": 4, "source_id": "DATA-01", "name": "가상 부두", "gu": "영도구"}]
    assert "lat" not in str(ev.bundle)  # 좌표는 프롬프트에 넣지 않는다
    assert ev.source_ids == ["DEV-SEED", "DATA-04", "DATA-01"]


def test_partial_level_adds_plot():
    ev = EVIDENCE["partial"].build(DETAIL, INFO)
    assert ev.bundle["work"]["plot"] == "부두에서 일어난 사건" and ev.bundle["spoiler"] == "partial"


def test_without_info():
    ev = EVIDENCE["partial"].build(DETAIL, None)
    assert "plot" not in ev.bundle["work"] and "keywords" not in ev.bundle["work"]
    assert info_from_stored(None) is None
    assert info_from_stored({"plot": "p"}).source_id == "DATA-04"
