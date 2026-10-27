import pytest

from app.data.models import Location, Point
from app.pipeline.travel import StationLink, estimate, haversine_m, walk_minutes
from app.services.map.service import cert_block_reason, in_busan

# 위도 0.001도 ≈ 111.2m


def test_walk_rule():
    assert walk_minutes(1000) == pytest.approx(19.5)  # 1000 × 1.3 ÷ (4000/60)


def rail(minutes):
    return lambda a, b: minutes


def test_walk_within_1km_never_uses_subway():
    a, b = (35.0, 129.0), (35.0069, 129.0)  # 직선 약 767m → 도보 거리 약 997m
    assert haversine_m(*a, *b) * 1.3 <= 1000
    leg = estimate(a, b, StationLink("1", 1), StationLink("2", 1), rail(1))
    assert leg.mode == "walk"


def test_over_1km_picks_faster_subway():
    a, b = (35.0, 129.0), (35.03, 129.0)  # 약 3.3km
    leg = estimate(a, b, StationLink("1", 3), StationLink("2", 4), rail(6))
    assert (leg.mode, leg.minutes) == ("subway", 13)


def test_over_1km_keeps_walk_when_subway_slower():
    a, b = (35.0, 129.0), (35.0081, 129.0)  # 약 900m 직선, 도보 약 1.17km
    leg = estimate(a, b, StationLink("1", 10), StationLink("2", 10), rail(5))
    assert leg.mode == "walk"


def test_same_nearest_station_is_walk():
    a, b = (35.0, 129.0), (35.03, 129.0)
    leg = estimate(a, b, StationLink("1", 3), StationLink("1", 4), rail(0))
    assert leg.mode == "walk"


def test_missing_rail_time_falls_back_to_walk():
    a, b = (35.0, 129.0), (35.03, 129.0)
    assert estimate(a, b, StationLink("1", 3), StationLink("2", 4), rail(None)).mode == "walk"


def loc(**kw):
    base = dict(
        id=1, name="x", address=None, gu=None, lat=35.1, lon=129.0, tags=[], caution="none", safety_note=None,
        cert_radius_m=100, cert_excluded=False, nearest_station_id=None, station_walk_min=None,
    )  # fmt: skip
    return Location(**{**base, **kw})


@pytest.mark.parametrize(
    ("kw", "reason"),
    [({}, None), ({"lat": None, "lon": None}, "no_coords"), ({"cert_excluded": True}, "excluded"),
     ({"caution": "school"}, "school"), ({"caution": "residential"}, "residential")],
)  # fmt: skip
def test_cert_block_reason(kw, reason):
    assert cert_block_reason(loc(**kw)) == reason


def test_in_busan():
    assert in_busan(Point(35.1152, 129.0422))
    assert not in_busan(Point(37.5665, 126.9780))  # 서울
