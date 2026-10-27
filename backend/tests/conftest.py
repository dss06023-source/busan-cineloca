import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql


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
