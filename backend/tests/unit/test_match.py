"""WorkMatcher(BR-11)와 MatchWorksStep. 경계값 0.6·0.9, 부제·공백만 다른 제목(build-plan 5장)."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.batch.job import SyncContext
from app.batch.steps import MatchWorksStep
from app.data.adapters.kmdb_csv import KmdbCsvCatalog
from app.data.adapters.policy import PolicyGuard
from app.data.models import StagedWork
from app.pipeline import match
from app.pipeline.match import WorkMatcher

FAKE = Path(__file__).resolve().parents[1] / "fixtures/fake/kmdb_basic.csv"


@dataclass(frozen=True)
class Cand:
    kmdb_id: str
    title: str
    prdt_year: int | None
    title_en: str | None = None
    title_org: str | None = None


def decide(title, year, *cands):
    return WorkMatcher().decide(title, year, cands)


def test_same_title_and_year_auto():
    assert decide("부산행", 2016, Cand("K1", "부산행", 2016)) == match.MatchResult("auto", "K1", 1.0)


@pytest.mark.parametrize("title", ["범죄도시 2", "범죄도시2", "범죄 도시2", "범죄도시: 2"])
def test_space_and_punctuation_only_differences_are_same_title(title):
    assert decide(title, 2022, Cand("K2", "범죄도시2", 2022)).status == "auto"


def test_production_vs_release_year_one_off_still_auto():
    r = decide("해운대", 2009, Cand("K3", "해운대", 2008))
    assert r.status == "auto" and r.score == pytest.approx(0.97)


def test_same_title_remake_far_year_goes_to_review():
    r = decide("친구", 2001, Cand("K4", "친구", 1972))
    assert (r.status, r.kmdb_id, r.score) == ("review", "K4", 0.7)


def test_picks_best_candidate():
    r = decide("친구", 2001, Cand("K4", "친구", 1972), Cand("K5", "친구", 2001))
    assert (r.status, r.kmdb_id) == ("auto", "K5")


def test_english_title_counts():
    assert decide("Train to Busan", 2016, Cand("K6", "부산행", 2016, title_en="Train to Busan")).status == "auto"


def test_no_candidates_unmatched():
    assert decide("없는영화", 2020) == match.MatchResult("unmatched", None, 0.0)


@pytest.mark.parametrize(
    ("score", "status"),
    [(0.9, "auto"), (0.8999, "review"), (0.6, "review"), (0.5999, "unmatched")],
)
def test_thresholds(monkeypatch, score, status):
    monkeypatch.setattr(match, "score", lambda *_: score)
    r = decide("아무거나", 2000, Cand("K7", "아무거나", 2000))
    assert r.status == status and (r.kmdb_id is None) == (status == "unmatched")


@pytest.fixture(scope="module")
def catalog():
    return KmdbCsvCatalog.load(FAKE)


def work(title, year, **kw):
    return StagedWork(f"t:{title}:{year}", title, title, year, "DATA-01", **kw)


async def run_step(catalog, works, policy="STORE", reviewed=None):
    async def reviewed_fn():
        return reviewed or {}

    ctx = SyncContext(works=works)
    await MatchWorksStep(catalog, PolicyGuard({"DATA-04": policy}), reviewed_fn).run(ctx)
    return {w.ext_key: w for w in ctx.works}


async def test_step_auto_fills_id_and_stored_plot(catalog):
    w = (await run_step(catalog, [work("가짜 부산 이야기", 2016)]))["t:가짜 부산 이야기:2016"]
    assert (w.kmdb_id, w.match_status, w.match_candidate) == ("K90002", "auto", None)
    assert w.kmdb["plot"] and w.kmdb["source_id"] == "DATA-04"


async def test_step_id_only_policy_keeps_no_plot(catalog):
    w = (await run_step(catalog, [work("가짜 부산 이야기", 2016)], policy="ID_ONLY"))["t:가짜 부산 이야기:2016"]
    assert w.kmdb_id == "K90002" and w.kmdb is None


async def test_step_review_range_leaves_candidate_only(catalog):
    w = (await run_step(catalog, [work("가짜 부산 이야기", 2005)]))["t:가짜 부산 이야기:2005"]
    assert (w.kmdb_id, w.match_status, w.kmdb) == (None, "unmatched", None)
    assert w.match_candidate in {"K90002", "K90004"} and 0.6 <= w.match_score < 0.9


async def test_step_uses_reviewed_match_without_rematching(catalog):
    w = work("가짜 부산 이야기", 2016)
    got = (await run_step(catalog, [w], reviewed={w.ext_key: "K90003"}))[w.ext_key]
    assert got.kmdb_id == "K90003" and got.kmdb["link"].endswith("/K/90003")
