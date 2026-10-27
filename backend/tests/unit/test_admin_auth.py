"""AdminAuth(FR-615): 5회 연속 실패 잠금 10분, 세션 2시간. 비밀번호는 테스트 전용 값."""

import pytest
from argon2 import PasswordHasher

from app.api.admin_auth import LOCK_S, MAX_FAILS, SESSION_S, AdminAuth
from app.api.errors import AppError

PW = "test-only-password"
HASH = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PW)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_lock_after_five_failures_then_unlock():
    clock = Clock()
    auth = AdminAuth(HASH, clock)
    for _ in range(MAX_FAILS):
        with pytest.raises(AppError) as e:
            auth.login("wrong")
        assert e.value.status == 401
    with pytest.raises(AppError) as e:
        auth.login(PW)  # 맞는 비밀번호도 잠금 중에는 거부
    assert e.value.status == 423 and e.value.retry_after == LOCK_S + 1
    clock.t += LOCK_S
    assert auth.check(auth.login(PW))


def test_success_resets_failures():
    auth = AdminAuth(HASH, Clock())
    for _ in range(MAX_FAILS - 1):
        with pytest.raises(AppError):
            auth.login("wrong")
    auth.login(PW)
    for _ in range(MAX_FAILS - 1):
        with pytest.raises(AppError) as e:
            auth.login("wrong")
        assert e.value.status == 401


def test_session_expires_and_logout():
    clock = Clock()
    auth = AdminAuth(HASH, clock)
    t = auth.login(PW)
    assert auth.check(t) and not auth.check("other") and not auth.check(None)
    clock.t += SESSION_S
    assert not auth.check(t)
    t2 = auth.login(PW)
    auth.logout(t2)
    assert not auth.check(t2)


def test_empty_hash_disables_login():
    with pytest.raises(AppError):
        AdminAuth("").login(PW)
