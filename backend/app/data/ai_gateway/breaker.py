"""CircuitBreaker: 연속 실패가 fails번이면 open_s초 동안 그 공급자를 건너뛴다. 지나면 한 번 시험(half-open)."""

import time
from collections.abc import Callable


class CircuitBreaker:
    def __init__(self, fails: int, open_s: float, clock: Callable[[], float] = time.monotonic):
        self.fails = fails
        self.open_s = open_s
        self.clock = clock
        self.count = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half_open" if self.clock() - self.opened_at >= self.open_s else "open"

    def allow(self) -> bool:
        return self.state != "open"

    def record(self, ok: bool) -> None:
        if ok:
            self.count, self.opened_at = 0, None
            return
        self.count += 1
        if self.count >= self.fails or self.state == "half_open":
            self.opened_at = self.clock()
