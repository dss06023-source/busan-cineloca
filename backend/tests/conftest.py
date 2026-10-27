import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from psycopg.rows import dict_row

from app.data.db import make_pool
from app.data.migrate import migrate

FIXTURE = Path(__file__).resolve().parent / "fixtures/templates_fixture.sql"


@pytest.fixture(scope="session")
def db_url() -> Iterator[str]:
    """TEST_DATABASE_URL 서버에 빈 DB를 새로 만들고 끝나면 지운다(integration 표시 테스트 전용)."""
    admin = os.environ.get("TEST_DATABASE_URL")
    if not admin:
        pytest.fail("integration 테스트에는 TEST_DATABASE_URL이 필요합니다. DB 없이 돌리려면 -m 'not integration'")
    name = f"cl_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = psycopg.conninfo.make_conninfo(admin, dbname=name)
    try:
        yield url
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture(scope="session")
def seeded_url(db_url) -> str:
    """마이그레이션을 모두 적용하고 템플릿 픽스처(가짜 데이터)를 넣은 DB."""
    migrate(db_url)
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute(FIXTURE.read_text(encoding="utf-8"))
    return db_url


@pytest.fixture(scope="session")
def conn(seeded_url):
    with psycopg.connect(seeded_url, row_factory=dict_row, autocommit=True) as c:
        yield c


@pytest.fixture(scope="session")
async def pool(seeded_url):
    p = make_pool(seeded_url)
    await p.open()
    yield p
    await p.close()
