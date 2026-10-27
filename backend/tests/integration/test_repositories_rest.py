"""Work·Course·Dictionary·Review·Sync·AICache·Usage 저장소(템플릿 픽스처 기준)."""

from datetime import date

import pytest

from app.data.models import Course, CourseStop, SyncRun, WorkQuery
from app.data.repositories.ai_cache import AICacheRepository
from app.data.repositories.course import CourseRepository
from app.data.repositories.dictionary import DictionaryRepository
from app.data.repositories.review import ReviewRepository
from app.data.repositories.sync import SyncRepository
from app.data.repositories.usage import UsageRepository
from app.data.repositories.work import WorkRepository

pytestmark = pytest.mark.integration


async def test_work_page_sort_and_filters(pool):
    repo = WorkRepository(pool)
    by_locations = await repo.page(WorkQuery())
    assert by_locations.total == 4
    # retired 촬영지(영도대교)는 개수에서 빠진다. 같은 개수면 최신작이 먼저
    assert [(w.title, w.location_count) for w in by_locations.items] == [
        ("범죄도시", 2),
        ("해운대", 2),
        ("친구", 1),
        ("부산행", 0),
    ]
    by_year = await repo.page(WorkQuery(sort="year"))
    assert [w.release_year for w in by_year.items] == [2017, 2016, 2009, 2001]
    assert [w.title for w in (await repo.page(WorkQuery(q="범죄 도시"))).items] == ["범죄도시"]
    assert (await repo.page(WorkQuery(genre="드라마"))).total == 2
    assert (await repo.page(WorkQuery(page=2))).items == []
    with pytest.raises(ValueError):
        await repo.page(WorkQuery(sort="title"))


async def test_work_detail(pool):
    detail = await WorkRepository(pool).get(1)
    assert detail.work.title == "범죄도시"
    assert [(p.name, p.role) for p in detail.people] == [("마동석", "actor")]
    assert [loc.name for loc in detail.locations] == ["광안리해수욕장", "서면 젊음의거리"]
    assert detail.source_ids == ["DATA-01"]
    assert await WorkRepository(pool).get(999) is None


async def test_course_save_and_read(pool):
    repo = CourseRepository(pool)
    course = Course(
        theme="area",
        title="서면 반나절",
        start_label="서면역",
        start_lat=35.1579,
        start_lon=129.0594,
        total_min=120,
        total_m=3000,
        stops=[CourseStop(ord=1, location_id=3), CourseStop(ord=2, location_id=2, leg_mode="subway", leg_min=18)],
    )
    cid = await repo.save(course)
    assert await repo.approved() == []
    saved = await repo.get(cid)
    assert [s.location_id for s in saved.stops] == [3, 2] and saved.stops[1].leg_mode == "subway"
    await repo.save(Course(**{**saved.__dict__, "status": "approved", "stops": saved.stops[:1]}))
    assert [c.id for c in await repo.approved("area")] == [cid]
    assert await repo.approved("work") == []
    assert len(await repo.stops(cid)) == 1


async def test_dictionary_fuzzy_and_semantic(pool, conn):
    vec = [0.0] * 1024
    vec[0] = 1.0
    conn.execute(
        "INSERT INTO dict_entry(kind, surface, canonical_id, embedding) VALUES"
        " ('person', '마동석', '1', %(v)s::vector), ('person', '마동욱', '9', NULL)",
        {"v": str(vec).replace(" ", "")},
    )
    repo = DictionaryRepository(pool)
    hits = await repo.fuzzy("person", "마 동석")
    assert hits[0].canonical_id == "1" and hits[0].score == 1.0
    sem = await repo.semantic("person", vec)
    assert [h.canonical_id for h in sem] == ["1"] and round(sem[0].score, 3) == 1.0
    with pytest.raises(ValueError):
        await repo.fuzzy("place", "x")


async def test_review_queue(pool):
    repo = ReviewRepository(pool)
    rid = await repo.add("tag", "location", 1, {"tags": ["바다"]}, "ai", model="fake", score=0.8)
    assert [i.id for i in await repo.pending("tag")] == [rid]
    decided = await repo.decide(rid, "approved", "admin")
    assert decided.status == "approved"
    assert await repo.decide(rid, "rejected", "admin") is None
    assert await repo.pending("tag") == []


async def test_sync_request_claim_and_save(pool):
    repo = SyncRepository(pool)
    rid = await repo.request("admin")
    run = await repo.next_requested()
    assert (run.id, run.status) == (rid, "running")
    assert await repo.next_requested() is None
    await repo.save(SyncRun(**{**run.__dict__, "status": "rejected", "counts": {"location": 3}, "failures": []}))
    latest = (await repo.recent(1))[0]
    assert (latest.status, latest.counts) == ("rejected", {"location": 3})


async def test_ai_cache_ttl(pool, conn):
    repo = AICacheRepository(pool)
    key = "a" * 64
    await repo.put(key, "extract_query", {"result_type": "LOCATION"})
    assert await repo.get(key) == {"result_type": "LOCATION"}
    conn.execute("UPDATE ai_cache SET expires_at = now() - interval '1 second' WHERE key = %(k)s", {"k": key})
    assert await repo.get(key) is None
    assert await repo.purge_expired() == 1


async def test_usage_counter(pool):
    repo = UsageRepository(pool)
    day = date(2026, 1, 1)
    assert await repo.get(day, "gemini:x") == 0
    assert await repo.incr(day, "gemini:x") == 1
    assert await repo.incr(day, "gemini:x", by=2) == 3
