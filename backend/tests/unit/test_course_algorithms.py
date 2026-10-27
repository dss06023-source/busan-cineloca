"""build-plan 5장 '꼭 넣을 단위 테스트': NearestNeighbor2Opt, BudgetFitter, CandidateScorer."""

import itertools
import random

import pytest

from app.pipeline.course.route import (
    Place,
    RoutePlanner,
    TravelModel,
    held_karp,
    nearest_neighbor_2opt,
    path_cost,
)
from app.pipeline.course.scoring import BudgetFitter, Candidate, CandidateScorer, CourseInfeasible, Preference

START = Place(None, "출발", 35.1152, 129.0422)


def random_places(rng: random.Random, n: int) -> list[Place]:
    return [Place(i, f"장소{i}", 35.05 + rng.random() * 0.15, 128.95 + rng.random() * 0.25) for i in range(1, n + 1)]


def exhaustive(cost):
    n = len(cost)
    return min(path_cost([0, *p], cost) for p in itertools.permutations(range(1, n)))


def costs(n, seed):
    model = TravelModel()
    points = [START, *random_places(random.Random(seed), n)]
    return [[0.0 if a is b else model.leg(a, b).minutes for b in points] for a in points]


@pytest.mark.parametrize("n", [1, 3, 5, 7, 8])
def test_planner_optimal_up_to_8(n):
    """AI-REQ-11: 8곳 이하에서 완전 탐색 대비 +10% 이내. RoutePlanner는 9곳 이하에서 정확해를 쓴다."""
    for seed in range(15):
        cost = costs(n, seed)
        order = held_karp(cost)
        assert order[0] == 0 and sorted(order) == list(range(n + 1))
        assert path_cost(order, cost) == pytest.approx(exhaustive(cost))


def test_nn2opt_heuristic_is_valid_and_close_on_average():
    """10곳 이상에서 쓰는 휴리스틱: 순서가 올바르고, 7곳 무작위 50개 평균이 최적 대비 +5% 이내."""
    ratios = []
    for seed in range(50):
        cost = costs(7, seed)
        order = nearest_neighbor_2opt(cost)
        assert order[0] == 0 and sorted(order) == list(range(8))
        ratios.append(path_cost(order, cost) / exhaustive(cost))
    assert sum(ratios) / len(ratios) <= 1.05


def test_route_totals_and_fixed_order():
    rng = random.Random(1)
    stops = random_places(rng, 4)
    planner = RoutePlanner(TravelModel(), dwell_min=20)
    r = planner.plan(START, stops, fixed_order=True)
    assert [p.id for p in r.stops] == [1, 2, 3, 4] and len(r.legs) == 4
    assert r.total_min == sum(leg.minutes for leg in r.legs) + 80
    assert r.total_m == sum(leg.distance_m for leg in r.legs)
    best = planner.plan(START, stops)
    assert best.total_min <= r.total_min


def test_subway_leg_shows_line():
    a = Place(1, "a", 35.1152, 129.0422, "113", 2)
    b = Place(2, "b", 35.1634, 129.1586, "203", 2)
    model = TravelModel(rail={("113", "203"): 20}, lines={"113": "1호선", "203": "2호선"})
    leg = model.leg(a, b)
    assert leg.mode == "subway" and leg.minutes == 24 and leg.line == "1호선→2호선"


def cand(i, lat_off, works=1, tags=(), genres=(), gu="중구"):
    return Candidate(Place(i, f"장소{i}", 35.1152 + lat_off, 129.0422), gu, list(tags), list(genres), [i], [], works)


def test_scorer_weights_change_ranking():
    near_few = cand(1, 0.001, works=1)
    far_many = cand(2, 0.05, works=5)
    pref = Preference()
    dist_first = CandidateScorer({"preference": 0.0, "works": 0.1, "distance": 0.9}, 15, 10000)
    works_first = CandidateScorer({"preference": 0.0, "works": 0.9, "distance": 0.1}, 15, 10000)
    assert [s.candidate.place.id for s in dist_first.top([near_few, far_many], pref, START)] == [1, 2]
    assert [s.candidate.place.id for s in works_first.top([near_few, far_many], pref, START)] == [2, 1]


def test_scorer_preference_avoid_and_top_k():
    sea = cand(1, 0.01, tags=["바다"], genres=["로맨스"])
    stairs = cand(2, 0.01, tags=["계단", "야경"])
    plain = cand(3, 0.01)
    s = CandidateScorer(top_k=2)
    top = s.top([sea, stairs, plain], Preference(mood_tags=["바다"], avoid=["계단"]), START)
    assert [x.candidate.place.id for x in top] == [1, 3] and top[0].matched == ["mood_tags"]


def scored_line(n):
    s = CandidateScorer()
    cands = [cand(i, 0.004 * i, works=n - i) for i in range(1, n + 1)]
    return s.top(cands, Preference(), START)


def test_budget_1h_8h_and_three_candidates():
    fitter = BudgetFitter(RoutePlanner(TravelModel(), 20))
    with pytest.raises(CourseInfeasible) as e:
        fitter.fit(START, scored_line(10), 60)  # 체류만 3곳 60분 + 이동 → 3곳도 못 맞춤
    assert e.value.reason == "budget"
    route, chosen = fitter.fit(START, scored_line(10), 8 * 60)
    assert len(route.stops) == 8 and route.total_min <= 480  # 8곳 상한
    route, _ = fitter.fit(START, scored_line(3), 8 * 60)
    assert len(route.stops) == 3
    with pytest.raises(CourseInfeasible) as e:
        fitter.fit(START, scored_line(2), 8 * 60)
    assert e.value.reason == "candidates"


def test_budget_drops_lowest_score_first():
    fitter = BudgetFitter(RoutePlanner(TravelModel(), 20))
    route, chosen = fitter.fit(START, scored_line(6), 100)
    kept = {p.id for p in route.stops}
    assert route.total_min <= 100 and len(kept) >= 3
    assert kept == {s.candidate.place.id for s in chosen} and 6 not in kept
