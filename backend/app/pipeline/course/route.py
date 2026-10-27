"""RoutePlanner(NearestNeighbor2Opt, FR-304)와 구간 이동 시간(BR-12, FR-313).

코스(F3)와 관리자(추천 코스 후보)가 함께 쓴다.
"""

from dataclasses import dataclass, field
from typing import Literal

from app.pipeline.travel import DETOUR, StationLink, estimate, haversine_m


@dataclass(frozen=True)
class Place:
    """경로의 한 점. 출발지는 id가 None일 수 있다."""

    id: int | None
    name: str
    lat: float
    lon: float
    station_id: str | None = None
    station_walk_min: float | None = None


@dataclass(frozen=True)
class LegInfo:
    mode: Literal["walk", "subway"]
    minutes: int
    distance_m: int
    line: str | None = None


@dataclass(frozen=True)
class Route:
    start: Place
    stops: list[Place]
    legs: list[LegInfo]  # legs[i]: (출발지 또는 stops[i-1]) → stops[i]
    dwell_min: int
    total_min: int = 0
    total_m: int = 0


def _link(p: Place) -> StationLink | None:
    if p.station_id is None or p.station_walk_min is None:
        return None
    return StationLink(p.station_id, p.station_walk_min)


@dataclass
class TravelModel:
    """역간 소요시간 표와 역 노선을 받아 두 장소 사이 구간을 계산한다."""

    rail: dict[tuple[str, str], float] = field(default_factory=dict)
    lines: dict[str, str] = field(default_factory=dict)

    def leg(self, a: Place, b: Place) -> LegInfo:
        leg = estimate((a.lat, a.lon), (b.lat, b.lon), _link(a), _link(b), lambda x, y: self.rail.get((x, y)))
        distance = round(haversine_m(a.lat, a.lon, b.lat, b.lon) * DETOUR)
        line = None
        if leg.mode == "subway":
            la, lb = self.lines.get(a.station_id), self.lines.get(b.station_id)
            line = la if la == lb else f"{la}→{lb}"
        return LegInfo(leg.mode, max(1, round(leg.minutes)), distance, line)


def path_cost(order: list[int], cost: list[list[float]]) -> float:
    return sum(cost[order[k]][order[k + 1]] for k in range(len(order) - 1))


def _two_opt(order: list[int], cost: list[list[float]]) -> list[int] | None:
    best = path_cost(order, cost)
    for i in range(1, len(order) - 1):
        for j in range(i + 1, len(order)):
            cand = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
            if path_cost(cand, cost) < best - 1e-9:
                return cand
    return None


def _or_opt(order: list[int], cost: list[list[float]]) -> list[int] | None:
    """1~3곳 묶음을 다른 자리로 옮긴다. 열린 경로에서 2-opt만으로는 빠져나오지 못하는 배치를 푼다."""
    best = path_cost(order, cost)
    n = len(order)
    for size in (1, 2, 3):
        for i in range(1, n - size + 1):
            seg, rest = order[i : i + size], order[:i] + order[i + size :]
            for k in range(1, len(rest) + 1):
                if k == i:
                    continue
                cand = rest[:k] + seg + rest[k:]
                if path_cost(cand, cost) < best - 1e-9:
                    return cand
    return None


EXACT_MAX = 9  # 장소가 이 수 이하면 동적 계획법으로 최적 순서를 구한다(2^9 × 9² ≈ 4만 번)


def held_karp(cost: list[list[float]]) -> list[int]:
    """0번에서 시작해 모든 점을 한 번씩 지나는 최단 열린 경로(정확해)."""
    n = len(cost) - 1
    if n <= 0:
        return [0]
    best: dict[tuple[int, int], tuple[float, int]] = {}
    for j in range(n):
        best[(1 << j, j)] = (cost[0][j + 1], -1)
    for mask in range(1, 1 << n):
        for j in range(n):
            if not mask & (1 << j) or (mask, j) not in best:
                continue
            base = best[(mask, j)][0]
            for k in range(n):
                if mask & (1 << k):
                    continue
                key, c = (mask | (1 << k), k), base + cost[j + 1][k + 1]
                if key not in best or c < best[key][0] - 1e-9:
                    best[key] = (c, j)
    full = (1 << n) - 1
    j = min(range(n), key=lambda x: (best[(full, x)][0], x))
    order, mask = [], full
    while j != -1:
        order.append(j + 1)
        mask, j = mask ^ (1 << j), best[(mask, j)][1]
    return [0, *reversed(order)]


def nearest_neighbor_2opt(cost: list[list[float]]) -> list[int]:
    """0번(출발지)에서 시작하는 열린 경로. 최근접 이웃으로 순서를 정하고, 2-opt와 Or-opt 교환으로
    총 이동 시간이 더 줄지 않을 때까지 개선한다(FR-304)."""
    n = len(cost)
    order, left = [0], set(range(1, n))
    while left:
        last = order[-1]
        nxt = min(left, key=lambda j: (cost[last][j], j))
        order.append(nxt)
        left.remove(nxt)
    while (better := _two_opt(order, cost) or _or_opt(order, cost)) is not None:
        order = better
    return order


class RoutePlanner:
    MAX_STOPS = 16  # 후보 15 + 출발지

    def __init__(self, travel: TravelModel, dwell_min: int = 20):
        self.travel = travel
        self.dwell_min = dwell_min

    def plan(self, start: Place, stops: list[Place], fixed_order: bool = False) -> Route:
        if len(stops) + 1 > self.MAX_STOPS:
            raise ValueError("장소는 15곳까지")
        points = [start, *stops]
        if fixed_order:
            ordered = stops
        else:
            cost = [[0.0 if i == j else self.travel.leg(a, b).minutes for j, b in enumerate(points)]
                    for i, a in enumerate(points)]  # fmt: skip
            solve = held_karp if len(stops) <= EXACT_MAX else nearest_neighbor_2opt
            ordered = [points[k] for k in solve(cost)[1:]]
        legs, prev = [], start
        for p in ordered:
            legs.append(self.travel.leg(prev, p))
            prev = p
        total = sum(leg.minutes for leg in legs) + self.dwell_min * len(ordered)
        return Route(start, ordered, legs, self.dwell_min, total, sum(leg.distance_m for leg in legs))
