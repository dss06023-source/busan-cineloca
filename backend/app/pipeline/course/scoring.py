"""CandidateScorer(FR-309)와 BudgetFitter(FR-310). AI 맞춤 코스와 조건 직접 선택(FR-312)이 같이 쓴다."""

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from app.pipeline.course.route import Place, Route, RoutePlanner
from app.pipeline.travel import haversine_m

CONFIG = Path(__file__).resolve().parents[3] / "config" / "course.yaml"


@cache
def course_config(path: Path = CONFIG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Candidate:
    place: Place
    gu: str | None
    tags: list[str]
    genres: list[str]
    work_ids: list[int]
    person_ids: list[int]
    work_count: int
    caution: str = "none"
    similarity: float | None = None  # 취향 문장 임베딩과의 코사인 유사도(없으면 None)


@dataclass(frozen=True)
class Preference:
    """구조화한 취향(preference.v1을 표준 값으로 바꾼 것)."""

    genres: list[str] = field(default_factory=list)
    mood_tags: list[str] = field(default_factory=list)
    work_ids: list[int] = field(default_factory=list)
    person_ids: list[int] = field(default_factory=list)
    gus: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return self == Preference(avoid=self.avoid)


@dataclass(frozen=True)
class Scored:
    candidate: Candidate
    score: float
    matched: list[str]  # 선정 이유 템플릿에 쓴다


class CourseInfeasible(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _overlap(want: list, have: list) -> float | None:
    if not want:
        return None
    return len(set(want) & set(have)) / len(set(want))


class CandidateScorer:
    def __init__(self, weights: dict | None = None, top_k: int | None = None, distance_cap_m: float | None = None):
        conf = course_config()
        self.w = weights or conf["weights"]
        self.top_k = top_k or conf["top_k"]
        self.cap = distance_cap_m or conf["distance_cap_m"]

    def avoided(self, c: Candidate, pref: Preference) -> bool:
        words = set(c.tags) | {c.caution}
        return any(a in words or any(a in t for t in c.tags) for a in pref.avoid)

    def score(self, c: Candidate, pref: Preference, start: Place, max_works: int) -> Scored:
        parts = {
            "genres": _overlap(pref.genres, c.genres),
            "mood_tags": _overlap(pref.mood_tags, c.tags),
            "work_ids": _overlap(pref.work_ids, c.work_ids),
            "person_ids": _overlap(pref.person_ids, c.person_ids),
            "gus": _overlap(pref.gus, [c.gu] if c.gu else []),
            "similarity": c.similarity,
        }
        given = [v for v in parts.values() if v is not None]
        pref_score = sum(given) / len(given) if given else 0.5
        works = c.work_count / max_works if max_works else 0.0
        d = haversine_m(start.lat, start.lon, c.place.lat, c.place.lon)
        distance = max(0.0, 1 - d / self.cap)
        total = self.w["preference"] * pref_score + self.w["works"] * works + self.w["distance"] * distance
        matched = [k for k, v in parts.items() if v and k != "similarity"]
        return Scored(c, round(total, 6), matched)

    def top(self, candidates: list[Candidate], pref: Preference, start: Place) -> list[Scored]:
        pool = [c for c in candidates if not self.avoided(c, pref)]
        max_works = max((c.work_count for c in pool), default=0)
        scored = [self.score(c, pref, start, max_works) for c in pool]
        scored.sort(key=lambda s: (-s.score, s.candidate.place.id))
        return scored[: self.top_k]


class BudgetFitter:
    """경로를 만든 뒤 예산·8곳을 넘으면 점수가 가장 낮은 장소부터 빼고 다시 계산한다. 3곳 미만이면 CourseInfeasible."""

    def __init__(self, planner: RoutePlanner, max_stops: int | None = None, min_stops: int | None = None):
        conf = course_config()
        self.planner = planner
        self.max_stops = max_stops or conf["max_stops"]
        self.min_stops = min_stops or conf["min_stops"]

    def fit(self, start: Place, scored: list[Scored], budget_min: int) -> tuple[Route, list[Scored]]:
        chosen = sorted(scored, key=lambda s: -s.score)
        if len(chosen) < self.min_stops:
            raise CourseInfeasible("candidates")
        while True:
            route = self.planner.plan(start, [s.candidate.place for s in chosen])
            if route.total_min <= budget_min and len(chosen) <= self.max_stops:
                return route, chosen
            if len(chosen) <= self.min_stops:
                raise CourseInfeasible("budget")
            chosen = chosen[:-1]  # 점수가 가장 낮은 장소를 뺀다
