"""마이그레이션·검색 템플릿 T1~T4·상태 확인을 실제 PostgreSQL에서 확인한다(starter check_templates.py 이식)."""

from pathlib import Path

import httpx
import pytest

from app.config import Settings
from app.data.migrate import migrate
from app.main import create_app

pytestmark = pytest.mark.integration

SQL_DIR = Path(__file__).resolve().parents[2] / "app/data/repositories/sql"
BASE = dict(work_ids=None, person_ids=None, genres=None, gus=None, year_from=None, year_to=None, limit=20)
SEOMYEON = dict(lat=35.1579, lon=129.0594)


def walk_radius(minutes: int) -> float:
    return minutes * 4000 / 60 / 1.3  # build-plan 5장 도보 규칙


@pytest.fixture(scope="module")
def templates():
    matched = (SQL_DIR / "_matched.sql").read_text()
    return {p.stem: p.read_text().replace("{matched}", matched) for p in SQL_DIR.glob("t*.sql")}


def run(conn, templates, name, **params):
    return conn.execute(templates[name], {**BASE, **params}).fetchall()


def test_migrate_is_idempotent(conn, db_url):
    assert migrate(db_url) == []
    versions = [r["version"] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY 1")]
    assert versions == ["001", "002", "003", "004", "005"]


def test_korean_trigram_not_empty(conn):
    # C 로캘이면 한글 트라이그램이 비어 사전 대조가 전부 0점이 된다(build-plan 7장)
    assert conn.execute("SELECT show_trgm('마동석') <> '{}' AS ok").fetchone()["ok"]


def test_t1_person_filter(conn, templates):
    rows = run(conn, templates, "t1_filter", person_ids=[1])
    assert [r["name"] for r in rows] == ["광안리해수욕장", "서면 젊음의거리"]


def test_t1_genre_year_includes_location_without_coords(conn, templates):
    rows = run(conn, templates, "t1_filter", genres=["드라마"], year_from=2000, year_to=2010)
    assert [r["id"] for r in rows] == [1, 2, 5]


def test_t2_walk_10_min_from_seomyeon(conn, templates):
    rows = run(conn, templates, "t2_near_point", **SEOMYEON, radius_m=walk_radius(10))
    assert [(r["name"], round(r["dist_m"])) for r in rows] == [("서면 젊음의거리", 248)]


def test_t2_excludes_location_without_coords(conn, templates):
    rows = run(conn, templates, "t2_near_point", **SEOMYEON, radius_m=50000.0)
    assert 5 not in [r["id"] for r in rows]


def test_t3_any_station_walk_10_min_with_person(conn, templates):
    rows = run(conn, templates, "t3_near_station", person_ids=[1], base_station=None, minutes=10)
    assert [(r["name"], r["travel_min"]) for r in rows] == [("서면 젊음의거리", 4)]


def test_t3_from_station_by_subway(conn, templates):
    rows = run(conn, templates, "t3_near_station", base_station="119", minutes=30)
    assert [(r["id"], r["travel_min"]) for r in rows] == [(3, 4), (2, 29)]
    assert rows[1]["source_ids"] == ["DATA-01", "DATA-02"]


def test_t4_works_by_district(conn, templates):
    rows = run(conn, templates, "t4_works", gus=["수영구", "해운대구"])
    assert [(r["title"], r["location_count"]) for r in rows] == [("해운대", 2), ("범죄도시", 1)]


def test_t2_uses_earth_gist_index(conn, templates):
    conn.execute("SET enable_seqscan = off")
    plan = conn.execute("EXPLAIN " + templates["t2_near_point"], {**BASE, **SEOMYEON, "radius_m": 513.0})
    assert any("location_earth" in r["QUERY PLAN"] for r in plan.fetchall())
    conn.execute("RESET enable_seqscan")


async def test_health_ok_with_db(conn, db_url, tmp_path):
    conn.execute("INSERT INTO usage_counter VALUES (CURRENT_DATE, 'gemini:test', 3) ON CONFLICT DO NOTHING")
    app = create_app(Settings(database_url=db_url, log_dir=str(tmp_path)))
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["db"] == "ok" and body["ai_breakers"] == {}
    assert isinstance(body["gemini_usage"], dict)
