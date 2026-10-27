"""세션당 AI 요청 분당 한도(AI-REQ-15). uvicorn 워커가 1개라 메모리 토큰 버킷으로 충분하다."""

import math
import time
from collections.abc import Callable


class TokenBucketLimiter:
    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic):
        self.capacity = float(per_minute)
        self.rate = per_minute / 60.0
        self.clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}

    def acquire(self, key: str) -> int | None:
        """자리가 있으면 None, 없으면 다시 시도할 수 있을 때까지의 초를 돌려준다."""
        now = self.clock()
        tokens, last = self._buckets.get(key, (self.capacity, now))
        tokens = min(self.capacity, tokens + (now - last) * self.rate)
        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            return None
        self._buckets[key] = (tokens, now)
        return max(1, math.ceil((1.0 - tokens) / self.rate))
