"""요청 마감. AI를 쓰는 API는 요청을 받은 순간 7.5초짜리를 만들어 끝까지 넘긴다(build-plan 6장)."""

import time
from collections.abc import Callable


class Deadline:
    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self.at = clock() + seconds

    def left(self) -> float:
        return max(0.0, self.at - self.clock())

    def expired(self) -> bool:
        return self.left() <= 0
