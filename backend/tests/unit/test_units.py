from pathlib import Path

from app.api.ratelimit import TokenBucketLimiter
from app.data.migrate import pending
from app.support.privacy import MASK, mask, scrub


def test_token_bucket_refills_over_time():
    now = [0.0]
    limiter = TokenBucketLimiter(5, clock=lambda: now[0])
    assert [limiter.acquire("s") for _ in range(5)] == [None] * 5
    assert limiter.acquire("s") == 12  # 1개가 다시 차는 데 60/5초
    now[0] += 12
    assert limiter.acquire("s") is None
    assert limiter.acquire("s") is not None


def test_pending_orders_and_skips_applied(tmp_path: Path):
    for name in ["002_core.sql", "001_extensions.sql", "010_more.sql", "README.md", "3_bad.sql"]:
        (tmp_path / name).write_text("")
    assert [p.name for p in pending(set(), tmp_path)] == ["001_extensions.sql", "002_core.sql", "010_more.sql"]
    assert [p.name for p in pending({"001", "002"}, tmp_path)] == ["010_more.sql"]


def test_mask_kinds():
    text, kinds = mask("연락 010-1234-5678, a.b@ex.com, 900101-1234567, 1234-5678-9012-3456")
    assert text.count(MASK) == 4
    assert sorted(kinds) == ["card", "email", "phone", "rrn"]


def test_scrub_nested():
    assert scrub({"a": ["x@y.kr", 3], "b": None}) == {"a": [MASK, 3], "b": None}


def test_no_sql_outside_repositories():
    from app.tools.check_sql_location import violations

    assert violations() == []
