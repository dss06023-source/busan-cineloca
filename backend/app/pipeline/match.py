"""WorkMatcher(BR-11): 수집한 작품을 KMDb 후보와 제목 유사도·연도로 맞춘다.

점수 = 0.7 × 제목 유사도(정규화한 제목의 difflib 비율) + 0.3 × 연도 점수.
0.9 이상이면 자동 연결, 0.6 이상이면 검수 큐, 그 아래는 미매칭이다.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Literal, Protocol

from app.data.text import normalize

AUTO, REVIEW = 0.9, 0.6
TITLE_W, YEAR_W = 0.7, 0.3


class Candidate(Protocol):
    kmdb_id: str
    title: str
    title_en: str | None
    title_org: str | None
    prdt_year: int | None


@dataclass(frozen=True)
class MatchResult:
    status: Literal["auto", "review", "unmatched"]
    kmdb_id: str | None
    score: float


def year_score(a: int | None, b: int | None) -> float:
    """제작연도와 개봉연도는 1년쯤 어긋나는 일이 흔해 1년 차이까지는 거의 같게 본다."""
    if a is None or b is None:
        return 0.5
    return {0: 1.0, 1: 0.9, 2: 0.5}.get(abs(a - b), 0.0)


def title_similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return 1.0 if na == nb else SequenceMatcher(None, na, nb).ratio()


def score(title: str, year: int | None, cand: Candidate) -> float:
    titles = [t for t in (cand.title, cand.title_en, cand.title_org) if t]
    sim = max((title_similarity(title, t) for t in titles), default=0.0)
    return round(TITLE_W * sim + YEAR_W * year_score(year, cand.prdt_year), 4)


class WorkMatcher:
    def decide(self, title: str, year: int | None, candidates: Iterable[Candidate]) -> MatchResult:
        best = max(((score(title, year, c), c.kmdb_id) for c in candidates), default=None)
        if best is None:
            return MatchResult("unmatched", None, 0.0)
        s, kmdb_id = best
        if s >= AUTO:
            return MatchResult("auto", kmdb_id, s)
        if s >= REVIEW:
            return MatchResult("review", kmdb_id, s)
        return MatchResult("unmatched", None, s)
