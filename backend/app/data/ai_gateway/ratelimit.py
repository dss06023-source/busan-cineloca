"""공급자별 분당 한도 대기열. 자리가 없으면 마감 안에서만 기다린다(429를 받기 전에 서버가 줄을 세움)."""

import asyncio
import time
from collections.abc import Awaitable, Callable

from app.data.ai_gateway.deadline import Deadline


class RpmLimiter:
    def __init__(
        self,
        rpm: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.capacity = float(rpm)
        self.rate = rpm / 60.0
        self.tokens = float(rpm)
        self.clock = clock
        self.sleep = sleep
        self.last = clock()
        self.lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now

    async def acquire(self, until: Deadline, reserve_s: float = 0.0) -> bool:
        """자리를 얻으면 True. 기다려도 마감(− reserve_s) 전에 자리가 안 나면 기다리지 않고 False."""
        async with self.lock:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            wait = (1.0 - self.tokens) / self.rate
            if wait > until.left() - reserve_s:
                return False
            await self.sleep(wait)
            self._refill()
            self.tokens = max(0.0, self.tokens - 1.0)
            return True
