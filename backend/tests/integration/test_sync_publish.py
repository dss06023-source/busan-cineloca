"""동기화 반영(build-plan 7장): 두 번 돌려도 id와 관리자 편집 값이 그대로여야 한다."""

from datetime import date

import psycopg
import pytest

from app.batch.guard import CountGuard
from app.batch.job import SyncJob
from app.data.db import make_pool
from app.data.migrate import migrate
from app.data.models import StagedLocation, StagedShooting, StagedWork
from app.data.repositories.staging import StagingRepository
from app.data.repositories.sync import SyncRepository

pytestmark = pytest.mark.integration

WORKS = [
    StagedWork("t:해운대:2009", "해운대", "해운대", 2009, "DATA-01", ["드라마"], "K1", None, "auto", 0.95),
    StagedWork("t:친구:2001", "친구", "친구", 2001, "DATA-01", match_status="unmatched"),
]
LOCS = [
    StagedLocation("해운대해수욕장|해운대구", "해운대해수욕장", "해운대해수욕장", "해운대구 우동", "해운대구",
                   35.1587, 129.1604, "ok"),
    StagedLocation("범일동|동구", "범일동", "범일동", None, "동구", 35.14, 129.06, "ok"),
    StagedLocation("자갈치|중구", "자갈치시장", "자갈치시장", None, "중구"),
]  # fmt: skip
SHOOT = [
    StagedShooting("t:해운대:2009", "해운대해수욕장|해운대구", "DATA-01", {"no": 1}, date(2026, 10, 1)),
    StagedShooting("t:친구:2001", "범일동|동구", "DATA-01", {"no": 2}, date(2026, 10, 1)),
]


class Fixed:
    name = "collect"

    def __init__(self, works, locs, shoot):
        self.data = works, locs, shoot

    async def run(self, ctx):
        ctx.works[:], ctx.locations[:], ctx.shootings[:] = (list(x) for x in self.data)


@pytest.fixture
async def env(fresh_db):
    migrate(fresh_db)
    pool = make_pool(fresh_db)
    await pool.open()
    yield pool, fresh_db
    await pool.close()


SMALL = CountGuard(min_work=1, min_location=1)


async def sync(pool, data, guard=SMALL):
    runs = SyncRepository(pool)
    await runs.request("admin")
    run = await runs.next_requested()
    job = SyncJob([Fixed(*data)], StagingRepository(pool), runs, guard)
    return await job.run(run)


def ids(conn, table):
    return dict(conn.execute(f"SELECT ext_key, id FROM {table}").fetchall())


async def test_two_syncs_keep_ids_and_admin_edits(env):
    pool, url = env
    assert (await sync(pool, (WORKS, LOCS, SHOOT))).status == "published"
    with psycopg.connect(url, autocommit=True) as conn:
        first = ids(conn, "work"), ids(conn, "location")
        conn.execute(
            "UPDATE location SET tags = '{야경}', caution = 'residential', safety_note = '주민 배려',"
            " cert_radius_m = 150, cert_excluded = true WHERE ext_key = '해운대해수욕장|해운대구'"
        )
        conn.execute(
            "UPDATE location SET lat = 35.1, lon = 129.0, geocode_status = 'manual' WHERE ext_key = '자갈치|중구'"
        )
        conn.execute("UPDATE work SET kmdb_id = 'K7', match_status = 'reviewed' WHERE ext_key = 't:친구:2001'")

    r = await sync(pool, (WORKS, LOCS, SHOOT))
    assert r.status == "published" and r.counts["published"] == {"work": 2, "location": 3, "shooting": 2}
    with psycopg.connect(url, autocommit=True) as conn:
        assert (ids(conn, "work"), ids(conn, "location")) == first
        assert conn.execute(
            "SELECT tags, caution, safety_note, cert_radius_m, cert_excluded FROM location"
            " WHERE ext_key = '해운대해수욕장|해운대구'"
        ).fetchone() == (["야경"], "residential", "주민 배려", 150, True)
        manual = conn.execute("SELECT lat, lon, geocode_status FROM location WHERE ext_key = '자갈치|중구'").fetchone()
        assert manual == (35.1, 129.0, "manual")
        assert conn.execute("SELECT kmdb_id, match_status FROM work WHERE ext_key = 't:친구:2001'").fetchone() == (
            "K7", "reviewed",
        )  # fmt: skip


async def test_missing_rows_retire_and_return(env):
    pool, url = env
    await sync(pool, (WORKS, LOCS, SHOOT))
    # 줄어든 비율은 건수 가드 테스트에서 따로 본다
    r = await sync(pool, (WORKS[:1], LOCS[:1] + LOCS[2:], SHOOT[:1]), CountGuard(1, 1, max_drop=1))
    assert r.status == "published"
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT ext_key FROM work WHERE retired").fetchall() == [("t:친구:2001",)]
        assert conn.execute("SELECT ext_key FROM location WHERE retired").fetchall() == [("범일동|동구",)]
        assert conn.execute("SELECT count(*) FROM shooting").fetchone()[0] == 1
        before = ids(conn, "location")
    await sync(pool, (WORKS, LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM location WHERE retired").fetchone()[0] == 0
        assert ids(conn, "location") == before


async def test_guard_violation_keeps_service_data(env):
    pool, url = env
    await sync(pool, (WORKS, LOCS, SHOOT))
    r = await sync(pool, (WORKS[:1], LOCS[:1], SHOOT[:1]))  # 촬영지 3 → 1(67% 감소)
    assert r.status == "rejected" and any("촬영지가 직전 3건" in x for x in r.counts["guard"]["reasons"])
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM location WHERE NOT retired").fetchone()[0] == 3
        q = "SELECT status, prev_counts, finished_at IS NOT NULL FROM sync_run ORDER BY id DESC"
        row = conn.execute(q).fetchone()
        assert row == ("rejected", {"work": 2, "location": 3, "shooting": 2}, True)
