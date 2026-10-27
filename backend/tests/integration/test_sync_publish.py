"""동기화 반영(build-plan 7장): 두 번 돌려도 id와 관리자 편집 값이 그대로여야 한다."""

from dataclasses import replace
from datetime import date

import psycopg
import pytest

from app.batch.guard import CountGuard
from app.batch.job import SyncJob
from app.data.db import make_pool
from app.data.migrate import migrate
from app.data.models import StagedLocation, StagedShooting, StagedWork
from app.data.repositories.location import LocationRepository
from app.data.repositories.staging import StagingRepository
from app.data.repositories.sync import SyncRepository
from app.data.repositories.work import WorkRepository

pytestmark = pytest.mark.integration

WORKS = [
    StagedWork(
        "t:해운대:2009",
        "해운대",
        "해운대",
        2009,
        "DATA-01",
        ["드라마"],
        "K1",
        None,
        "auto",
        0.95,
        kmdb={"source_id": "DATA-04", "plot": "가짜 줄거리", "keywords": ["쓰나미"], "link": "https://x"},
    ),
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
        plot = conn.execute("SELECT kmdb->>'plot' FROM work WHERE ext_key = 't:해운대:2009'").fetchone()[0]
        assert plot == "가짜 줄거리"


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


async def test_match_candidate_goes_to_review_queue_once(env):
    pool, url = env
    works = [WORKS[0], replace(WORKS[1], match_score=0.7, match_candidate="K4")]
    await sync(pool, (works, LOCS, SHOOT))
    await sync(pool, (works, LOCS, SHOOT))  # 두 번 돌려도 한 건
    with psycopg.connect(url, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT r.proposal->>'kmdb_id', r.proposer, r.score FROM review_item r JOIN work w ON w.id = r.target_id"
            " WHERE r.kind = 'match' AND w.ext_key = 't:친구:2001'"
        ).fetchall()
        assert rows == [("K4", "rule", pytest.approx(0.7))]
        # 반려한 후보도 다시 올리지 않는다
        conn.execute("UPDATE review_item SET status = 'rejected'")
    await sync(pool, (works, LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT count(*) FROM review_item").fetchone()[0] == 1


async def test_reviewed_work_gets_stored_kmdb_for_its_own_id(env):
    pool, url = env
    await sync(pool, (WORKS, LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("UPDATE work SET kmdb_id = 'K7', match_status = 'reviewed' WHERE ext_key = 't:친구:2001'")
    stored = {"source_id": "DATA-04", "plot": "검수한 줄거리", "keywords": [], "link": "https://k7"}
    # 매칭 단계가 검수 연결(K7)로 채운 저장본은 반영되고, 다른 ID의 저장본은 무시된다
    await sync(pool, ([WORKS[0], replace(WORKS[1], kmdb_id="K7", kmdb=stored)], LOCS, SHOOT))
    await sync(pool, ([WORKS[0], replace(WORKS[1], kmdb_id="K8", kmdb={"plot": "다른 영화"})], LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        row = conn.execute("SELECT kmdb_id, kmdb->>'plot' FROM work WHERE ext_key = 't:친구:2001'").fetchone()
        assert row == ("K7", "검수한 줄거리")


async def test_set_match_clears_stored_kmdb_only_when_id_changes(env):
    pool, url = env
    await sync(pool, (WORKS, LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        wid = conn.execute("SELECT id FROM work WHERE ext_key = 't:해운대:2009'").fetchone()[0]
    repo = WorkRepository(pool)
    assert await repo.set_match(wid, "K1")  # 같은 ID 승인: 저장본 유지
    assert await repo.reviewed_matches() == {"t:해운대:2009": "K1"}
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT kmdb->>'plot' FROM work WHERE id = %s", (wid,)).fetchone()[0] == "가짜 줄거리"
    assert await repo.set_match(wid, "K9")  # 다른 ID: 다음 동기화가 채울 때까지 비움
    with psycopg.connect(url, autocommit=True) as conn:
        assert conn.execute("SELECT kmdb FROM work WHERE id = %s", (wid,)).fetchone()[0] is None


async def test_geocoded_returns_only_ok_rows_with_address(env):
    pool, url = env
    await sync(pool, (WORKS, LOCS, SHOOT))
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("UPDATE location SET geocode_status = 'manual' WHERE ext_key = '자갈치|중구'")
    # 해운대해수욕장: ok + 주소 있음 → 포함, 범일동: 주소 없음, 자갈치: manual → 제외
    assert await LocationRepository(pool).geocoded() == {
        "해운대해수욕장|해운대구": ("해운대구 우동", 35.1587, 129.1604)
    }
