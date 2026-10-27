"""CountGuard(BR-14)와 SyncJob 흐름(FR-612·613). DB 없이 가짜 저장소로 확인한다."""

from datetime import date

import pytest

from app.batch.guard import CountGuard
from app.batch.job import SyncJob
from app.data.models import StagedLocation, StagedShooting, StagedWork, SyncRun

RUN = SyncRun(id=1, trigger="manual", status="running", requested_by="admin")


def test_guard_passes_first_sync_above_minimum():
    assert CountGuard().check({"work": 50, "location": 150}, {}).ok


@pytest.mark.parametrize(
    ("new", "prev", "hint"),
    [
        ({"work": 49, "location": 200}, {}, "작품 49건이 최소 기준 50건"),
        ({"work": 60, "location": 149}, {"work": 60, "location": 149}, "촬영지 149건이 최소 기준 150건"),
        ({"work": 70, "location": 200}, {"work": 100, "location": 200}, "작품이 직전 100건에서 70건으로 30%"),
    ],
)
def test_guard_rejects(new, prev, hint):
    r = CountGuard().check(new, prev)
    assert not r.ok and any(hint in x for x in r.reasons)


def test_guard_allows_drop_under_30_percent():
    assert CountGuard().check({"work": 71, "location": 200}, {"work": 100, "location": 200}).ok


class FakeStaging:
    def __init__(self, prev):
        self.loaded, self.published, self.prev = None, False, prev

    async def load(self, works, locations, shootings):
        self.loaded = (works, locations, shootings)

    async def staged_counts(self):
        w, loc, s = self.loaded
        return {"work": len(w), "location": len(loc), "shooting": len(s)}

    async def published_counts(self):
        return self.prev

    async def publish(self):
        self.published = True
        return await self.staged_counts()


class FakeRuns:
    def __init__(self):
        self.saved = []

    async def save(self, run):
        self.saved.append(run)


class Collect:
    name = "collect"

    async def run(self, ctx):
        ctx.works.append(StagedWork("w1", "해운대", "해운대", 2009, "DATA-01"))
        ctx.locations.append(StagedLocation("l1", "해운대해수욕장", "해운대해수욕장", None, "해운대구"))
        ctx.shootings.append(StagedShooting("w1", "l1", "DATA-01", {"n": 1}, date(2026, 10, 1)))
        ctx.failures.append({"step": "collect", "error": "주소 없음"})


class Boom:
    name = "geocode"

    async def run(self, ctx):
        raise RuntimeError("https://example.invalid/?key=secret")


async def test_job_publishes_when_guard_passes():
    staging, runs = FakeStaging({}), FakeRuns()
    r = await SyncJob([Collect()], staging, runs, CountGuard(min_work=1, min_location=1)).run(RUN)
    assert r.status == "published" and staging.published
    assert r.counts["guard"] == {"ok": True, "reasons": []}
    assert r.counts["steps"] == {"collect": {"work": 1, "location": 1}}
    assert r.failures == [{"step": "collect", "error": "주소 없음"}]
    assert runs.saved == [r]


async def test_job_rejects_and_keeps_service_data():
    staging, runs = FakeStaging({"work": 1, "location": 1}), FakeRuns()
    r = await SyncJob([], staging, runs, CountGuard(min_work=1, min_location=1)).run(RUN)
    assert r.status == "rejected" and not staging.published
    assert r.prev_counts == {"work": 1, "location": 1}
    assert r.counts["guard"]["ok"] is False


async def test_job_failure_records_step_without_message(caplog):
    staging, runs = FakeStaging({}), FakeRuns()
    r = await SyncJob([Collect(), Boom()], staging, runs).run(RUN)
    assert r.status == "failed" and staging.loaded is None
    assert r.failures[-1] == {"step": "geocode", "error": "RuntimeError"}
    # 예외 메시지(URL·키가 섞일 수 있음)는 기록·로그 어디에도 남지 않는다
    assert "secret" not in repr(r) and "secret" not in caplog.text
