"""BaseApiClient(COMP-11, SDD CD-05): 외부 데이터 API 공통 부분.

fetch_all()은 템플릿 메서드다. 페이지 반복, 3회 재시도, 응답 형식 검사, 하루 한도(80%) 관리는 여기서 하고
데이터별 하위 클래스는 page_params()·parse()(필요하면 check())만 구현한다(FR-601, NFR-018).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any, ClassVar, Protocol

import httpx

from app.data.adapters.config import AdapterConf
from app.data.adapters.errors import AdapterError, AdapterTimeout, QuotaExhausted, ResponseFormatError

log = logging.getLogger(__name__)

MAX_PAGES = 1000  # 원본이 totalCount를 잘못 줘도 끝나게


class UsageCounter(Protocol):
    async def incr(self, day: date, key: str, by: int = 1) -> int: ...
    async def get(self, day: date, key: str) -> int: ...


class BaseApiClient[T](ABC):
    name: ClassVar[str]
    list_path: ClassVar[str] = ""

    def __init__(
        self,
        http: httpx.AsyncClient,
        key: str,
        conf: AdapterConf,
        usage: UsageCounter | None = None,
        today: Callable[[], date] = date.today,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.http, self.key, self.conf = http, key, conf
        self.usage, self.today, self.sleep = usage, today, sleep

    @property
    def usage_key(self) -> str:
        return f"api:{self.name}"

    # 하위 클래스가 정하는 부분

    @abstractmethod
    def auth_params(self) -> dict[str, str]:
        """키를 넣는 쿼리 매개변수. 기관마다 이름이 다르다."""

    @abstractmethod
    def page_params(self, page: int) -> dict[str, Any]: ...

    @abstractmethod
    def parse(self, payload: Any) -> tuple[list[T], int]:
        """한 페이지 응답 → (레코드, 전체 건수). 구조가 다르면 ResponseFormatError."""

    def check(self, payload: Any) -> None:  # noqa: B027 - 기관 오류 응답이 있는 하위 클래스만 덮어쓴다
        """200으로 온 기관 오류 응답을 걸러 ResponseFormatError로 바꾼다."""

    # 공통 부분

    async def fetch_all(self, path: str | None = None, **query: Any) -> list[T]:
        out: list[T] = []
        for page in range(1, MAX_PAGES + 1):
            payload = await self.request(path or self.list_path, {**query, **self.page_params(page)})
            records, total = self.parse(payload)
            out.extend(records)
            if not records or len(out) >= total:
                break
        return out

    async def request(
        self, path: str, params: dict[str, Any], *, timeout_s: float | None = None, retries: int | None = None
    ) -> Any:
        """GET 한 번(실패하면 retries번까지). 5xx·429·연결 실패·시간 초과만 다시 보낸다."""
        await self._check_quota()
        attempts = retries or self.conf.retries
        url = f"{self.conf.base_url}/{path}" if path else self.conf.base_url
        last: AdapterError = AdapterError(f"{self.name}: no attempt")
        for n in range(1, attempts + 1):
            if n > 1:
                await self.sleep(self.conf.backoff_s * 2 ** (n - 2))
            await self._count()
            try:
                r = await self.http.get(
                    url, params={**params, **self.auth_params()}, timeout=timeout_s or self.conf.timeout_s
                )
            except httpx.TimeoutException:
                last = AdapterTimeout(f"{self.name}: timeout")
                continue
            except httpx.TransportError as e:  # 메시지에 URL(키)이 섞일 수 있어 종류만 남긴다
                last = AdapterError(f"{self.name}: {type(e).__name__}")
                continue
            if r.status_code == 429 or r.status_code >= 500:
                last = AdapterError(f"{self.name}: http {r.status_code}")
                continue
            if r.status_code >= 400:
                raise AdapterError(f"{self.name}: http {r.status_code}")
            try:
                payload = r.json()
            except ValueError:
                raise ResponseFormatError(f"{self.name}: not json") from None
            self.check(payload)
            return payload
        log.info("adapter gave up", extra={"provider": self.name, "error_code": type(last).__name__})
        raise last

    async def _check_quota(self) -> None:
        if self.usage and await self.usage.get(self.today(), self.usage_key) >= self.conf.quota:
            raise QuotaExhausted(f"{self.name}: daily quota {self.conf.quota}")

    async def _count(self) -> None:
        if self.usage:
            await self.usage.incr(self.today(), self.usage_key)
