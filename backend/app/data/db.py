"""PostgreSQL 연결 풀. 앱 수명 주기에서 열고 닫는다."""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def make_pool(dsn: str) -> AsyncConnectionPool:
    # open=False: 앱 시작 때 open()을 부른다. DB가 늦게 떠도 앱은 뜨고 /api/health가 down을 알린다.
    return AsyncConnectionPool(
        dsn,
        min_size=1,
        max_size=10,
        open=False,
        timeout=3.0,
        kwargs={"row_factory": dict_row, "autocommit": True},
    )
