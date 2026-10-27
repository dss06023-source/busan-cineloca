"""AdminAuth(FR-615): 관리자 비밀번호(argon2 해시) 확인과 쿠키 세션.

5회 연속 실패하면 10분 동안 423으로 막는다(ERR-012). 비밀번호·세션 값은 로그에 남기지 않는다.
세션은 메모리에만 두므로 api를 다시 시작하면 다시 로그인한다.
"""

import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Request

from app.api.errors import AppError

COOKIE = "cl_admin"
SESSION_S = 2 * 60 * 60
MAX_FAILS = 5
LOCK_S = 10 * 60


class AdminAuth:
    def __init__(self, password_hash: str, clock=time.monotonic):
        self.hash = password_hash
        self.clock = clock
        self.hasher = PasswordHasher()
        self.fails = 0
        self.locked_until = 0.0
        self.sessions: dict[str, float] = {}

    def login(self, password: str) -> str:
        now = self.clock()
        if now < self.locked_until:
            raise AppError("ERR-012", "로그인 시도가 많아 잠시 막았습니다", status=423,
                           retry_after=int(self.locked_until - now) + 1)  # fmt: skip
        ok = False
        if self.hash:  # 해시가 없으면 관리 기능을 끈다
            try:
                ok = self.hasher.verify(self.hash, password)
            except (VerificationError, InvalidHashError):
                ok = False
        if not ok:
            self.fails += 1
            if self.fails >= MAX_FAILS:
                self.fails = 0
                self.locked_until = now + LOCK_S
            raise AppError("ERR-012")
        self.fails = 0
        token = secrets.token_urlsafe(32)
        self.sessions = {t: exp for t, exp in self.sessions.items() if exp > now}
        self.sessions[token] = now + SESSION_S
        return token

    def check(self, token: str | None) -> bool:
        exp = self.sessions.get(token or "")
        if exp is None or exp <= self.clock():
            self.sessions.pop(token or "", None)
            return False
        return True

    def logout(self, token: str | None) -> None:
        self.sessions.pop(token or "", None)


def require_admin(request: Request) -> str:
    """관리자 API 의존성. 처리자 기록용 이름을 돌려준다(관리자는 한 명)."""
    if not request.app.state.admin_auth.check(request.cookies.get(COOKIE)):
        raise AppError("ERR-012")
    return "admin"
