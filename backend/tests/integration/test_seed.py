"""미니 시드 적재와 시연 장면 1·3·5 검색, 시드 내보내기 왕복(WP-02 끝 기준)."""

from pathlib import Path

import psycopg
import pytest

from app.data.db import make_pool
from app.data.models import Conditions, Point
from app.data.repositories.location import LocationRepository
from app.data.repositories.templates import walk_radius_m
from app.data.seed import export, load

pytestmark = pytest.mark.integration

MINI_SEED = Path(__file__).resolve().parents[3] / "db/seed/mini_seed.sql"
HAEUNDAE_STATION = Point(35.1634, 129.1586)


@pytest.fixture
async def seeded_pool(fresh_db):
    load(fresh_db, MINI_SEED)
    pool = make_pool(fresh_db)
    await pool.open()
    yield pool
    await pool.close()


def counts(dsn: str) -> dict:
    with psycopg.connect(dsn) as conn:
        return {
            t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in ("location", "work", "person", "shooting", "station", "station_time", "dict_entry", "source")
        }


async def test_mini_seed_counts(seeded_pool, fresh_db):
    c = counts(fresh_db)
    assert (c["location"], c["work"], c["station"], c["station_time"]) == (21, 10, 12, 144)
    assert c["source"] == 13  # DATA-01~12 + DEV-SEED


async def test_scene1_map_near_haeundae(seeded_pool):
    hits = await LocationRepository(seeded_pool).within_radius(HAEUNDAE_STATION, 1000)
    assert [h.name for h in hits] == ["해운대해수욕장", "더베이101"]
    assert all(h.source_ids == ["DEV-SEED"] for h in hits)


async def test_scene3_person_walk_10_from_any_station(seeded_pool):
    # 실제 시연 질의는 '마동석'. 미니 시드는 가짜 인물 '강도윤'(id 1)으로 같은 경로를 확인한다
    hits = await LocationRepository(seeded_pool).search(Conditions(person_ids=[1], any_station_walk_min=10))
    assert [(h.name, h.travel_min) for h in hits] == [
        ("부산역 광장", 2),
        ("자갈치시장", 3),
        ("서면 젊음의거리", 4),
        ("영도대교", 9),
    ]


async def test_scene5_certifiable_location_with_coords(seeded_pool):
    loc = await LocationRepository(seeded_pool).get(1)
    assert loc.lat is not None and not loc.cert_excluded and loc.cert_radius_m == 100


async def test_walk_radius_from_station(seeded_pool):
    hits = await LocationRepository(seeded_pool).within_radius(Point(35.1579, 129.0594), round(walk_radius_m(10)))
    assert [h.name for h in hits] == ["서면 젊음의거리"]


async def test_load_refuses_non_empty(seeded_pool, fresh_db):
    with pytest.raises(SystemExit):
        load(fresh_db, MINI_SEED)


async def test_export_round_trip(seeded_pool, fresh_db, other_db, tmp_path):
    dump = tmp_path / "seed.sql.gz"
    export(fresh_db, dump)
    load(other_db, dump)
    assert counts(other_db) == counts(fresh_db)
