"""TravelTimeEstimator(BR-12): 두 지점 사이 이동 시간 근사. 지도(F2)와 코스(F3)가 함께 쓴다."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

EARTH_R_M = 6_371_000
WALK_M_PER_MIN = 4000 / 60  # 시속 4km
DETOUR = 1.3  # 직선거리 보정
SUBWAY_THRESHOLD_M = 1000  # 도보 거리가 이보다 길면 도시철도와 비교


@dataclass(frozen=True)
class StationLink:
    """지점과 최근접 역, 그 역까지 도보 시간."""

    station_id: str
    walk_min: float


@dataclass(frozen=True)
class Leg:
    mode: Literal["walk", "subway"]
    minutes: float
    walk_m: float


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_M * math.asin(math.sqrt(a))


def walk_minutes(distance_m: float) -> float:
    return distance_m * DETOUR / WALK_M_PER_MIN


def estimate(
    a: tuple[float, float],
    b: tuple[float, float],
    a_station: StationLink | None = None,
    b_station: StationLink | None = None,
    rail_minutes: Callable[[str, str], float | None] | None = None,
) -> Leg:
    """도보 거리가 1km 이하면 도보. 넘으면 '역까지 도보 + 역간 시간 + 내려서 도보'와 비교해 짧은 쪽.

    같은 역이 두 지점의 최근접 역이면 도시철도를 탈 일이 없으므로 도보로 본다. 역간 시간이 없으면 도보만 쓴다.
    """
    straight = haversine_m(*a, *b)
    walk = Leg("walk", walk_minutes(straight), straight * DETOUR)
    if straight * DETOUR <= SUBWAY_THRESHOLD_M or a_station is None or b_station is None or rail_minutes is None:
        return walk
    if a_station.station_id == b_station.station_id:
        return walk
    rail = rail_minutes(a_station.station_id, b_station.station_id)
    if rail is None:
        return walk
    by_subway = a_station.walk_min + rail + b_station.walk_min
    walked_m = (a_station.walk_min + b_station.walk_min) * WALK_M_PER_MIN
    return Leg("subway", by_subway, walked_m) if by_subway < walk.minutes else walk


def station_label(name: str) -> str:
    """역 이름 표시. 원본에 '부산역'처럼 '역'이 붙은 이름이 있어 두 번 붙이지 않는다."""
    return name if name.endswith("역") else f"{name}역"
