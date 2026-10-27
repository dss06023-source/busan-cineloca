import pytest

from app.data.models import Conditions, Point
from app.data.repositories import templates as t


def test_walk_radius_rule():
    assert round(t.walk_radius_m(10)) == 513  # 10분 × 4000/60 ÷ 1.3


@pytest.mark.parametrize(
    ("cond", "expected"),
    [
        (Conditions(), t.T1_FILTER),
        (Conditions(person_ids=[1], result_type="WORK"), t.T4_WORKS),
        (Conditions(point=Point(35.1, 129.0), radius_m=500), t.T2_NEAR_POINT),
        (Conditions(any_station_walk_min=10), t.T3_NEAR_STATION),
        (Conditions(from_station="119", minutes=30), t.T3_NEAR_STATION),
    ],
)
def test_choose_template(cond, expected):
    assert t.choose(cond)[0] is expected


def test_empty_lists_become_none():
    _, params = t.choose(Conditions(genres=[], gus=["수영구"]))
    assert params["genres"] is None and params["gus"] == ["수영구"]


def test_station_params():
    _, any_station = t.choose(Conditions(any_station_walk_min=10))
    assert any_station["base_station"] is None and any_station["minutes"] == 10
    _, from_station = t.choose(Conditions(from_station="119", minutes=30))
    assert from_station["base_station"] == "119" and from_station["minutes"] == 30


@pytest.mark.parametrize("limit", [0, 21])
def test_limit_allowlist(limit):
    with pytest.raises(ValueError):
        t.choose(Conditions(), limit)


def test_map_limit_is_larger_but_bounded():
    assert t.choose(Conditions(), 300, max_limit=t.MAP_MAX_LIMIT)[1]["limit"] == 300
    with pytest.raises(ValueError):
        t.choose(Conditions(), 301, max_limit=t.MAP_MAX_LIMIT)
    with pytest.raises(ValueError):
        t.choose(Conditions(), 10, max_limit=999)


def test_incomplete_movement_conditions_rejected():
    with pytest.raises(ValueError):
        t.choose(Conditions(point=Point(35.1, 129.0)))
    with pytest.raises(ValueError):
        t.choose(Conditions(from_station="119"))
