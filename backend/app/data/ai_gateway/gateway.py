"""LLMClient(COMP-08): 기능 코드는 generate(task, inputs, deadline)만 부른다(build-plan 6장).

공급자 선택, 제한 시간, 재시도, 캐시, 호출 수 제한, 스키마 검증은 모두 여기서 하고, 실패하면 AIUnavailable.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.data.ai_gateway import prompts
from app.data.ai_gateway.breaker import CircuitBreaker
from app.data.ai_gateway.config import AIConfig
from app.data.ai_gateway.deadline import Deadline
from app.data.ai_gateway.errors import AIUnavailable, ProviderError, RateLimited, SchemaError
from app.data.ai_gateway.providers import Provider
from app.data.ai_gateway.ratelimit import RpmLimiter
from app.data.ai_gateway.schema import load_schema, validate

log = logging.getLogger(__name__)
PACIFIC = ZoneInfo("America/Los_Angeles")  # Gemini 하루 한도 초기화 기준
MAX_RETRY_AFTER_S = 2.0


class _NoTime(Exception):
    """재요청할 시간이 없음. 공급자 실패가 아니므로 차단기에 세지 않는다."""


@dataclass(frozen=True)
class LLMResult:
    data: dict
    provider: str
    cached: bool
    prompt_version: str


class Cache:
    """AICacheRepository와 같은 모양. 테스트는 dict로 대신한다."""

    async def get(self, key: str) -> dict | None: ...
    async def put(self, key: str, task: str, value: dict, ttl_h: int = 24) -> None: ...


class Usage:
    async def incr(self, day: date, key: str, by: int = 1) -> int: ...
    async def get(self, day: date, key: str) -> int: ...


def cache_key(task: str, version: str, inputs: dict, schema: dict) -> str:
    """작업 + 프롬프트 버전 + (마스킹한) 입력 + 근거 + 스키마의 SHA-256. 입력에 근거 묶음이 들어 있다."""
    payload = json.dumps([task, version, inputs, schema], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


class LLMClient:
    def __init__(
        self,
        config: AIConfig,
        providers: dict[str, Provider],
        cache: Cache,
        usage: Usage,
        today: Callable[[], date] = lambda: datetime.now(PACIFIC).date(),
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ):
        self.config = config
        self.providers = providers
        self.cache = cache
        self.usage = usage
        self.today = today
        self.breakers = {n: CircuitBreaker(config.breaker_fails, config.breaker_open_s) for n in providers}
        rpm = {n: config.providers[n].rpm if n in config.providers else 1000 for n in providers}
        self.rpm = {n: RpmLimiter(rpm[n], **({"sleep": sleep} if sleep else {})) for n in providers}
        self._sleep = sleep

    def breaker_states(self) -> dict[str, str]:
        return {n: b.state for n, b in self.breakers.items()}

    def chain(self, task: str) -> list[Provider]:
        """설정 순서대로, 켜진(등록된) 공급자만. fake만 등록돼 있으면 fake 하나."""
        names = self.config.tasks[task].chain
        chain = [self.providers[n] for n in names if n in self.providers]
        if not chain and "fake" in self.providers:
            chain = [self.providers["fake"]]
        return chain

    def _usage_key(self, p: Provider) -> str:
        return f"{p.name}:{p.model}"

    async def _quota_exhausted(self, p: Provider) -> bool:
        conf = self.config.providers.get(p.name)
        if conf is None:
            return False
        return await self.usage.get(self.today(), self._usage_key(p)) >= conf.daily_limit

    async def generate(self, task: str, inputs: dict, deadline: Deadline, schema: dict | None = None) -> LLMResult:
        conf = self.config.tasks[task]
        schema = schema or load_schema(conf.schema)
        prompt = prompts.render(task, conf.prompt, inputs)
        key = cache_key(task, conf.prompt, inputs, schema)
        if (hit := await self.cache.get(key)) is not None:
            return LLMResult(hit, provider="cache", cached=True, prompt_version=conf.prompt)

        reasons: list[str] = []
        for p in self.chain(task):
            breaker = self.breakers[p.name]
            if not breaker.allow():
                reasons.append(f"{p.name}:breaker_open")
                continue
            if await self._quota_exhausted(p):
                reasons.append(f"{p.name}:daily_limit")
                continue
            timeout = min(conf.cap_s, deadline.left() - self.config.reserve_s)
            if timeout < p.min_timeout_s:
                reasons.append(f"{p.name}:no_time")
                break  # 시간이 모자라면 다음 공급자도 부르지 않는다
            if not await self.rpm[p.name].acquire(deadline, self.config.reserve_s + p.min_timeout_s):
                reasons.append(f"{p.name}:rpm")
                continue
            try:
                data = await self._call_validated(p, prompt, schema, task, deadline)
            except _NoTime:
                reasons.append(f"{p.name}:no_time")
                break
            except (ProviderError, SchemaError) as e:
                breaker.record(ok=False)
                reasons.append(f"{p.name}:{type(e).__name__}")
                log.info("ai provider failed", extra={"task": task, "provider": p.name, "error": type(e).__name__})
                continue
            breaker.record(ok=True)
            await self.cache.put(key, task, data, self.config.cache_ttl_h)
            return LLMResult(data, provider=p.name, cached=False, prompt_version=conf.prompt)
        raise AIUnavailable(task, reasons)

    async def _call_validated(self, p: Provider, prompt, schema: dict, task: str, deadline: Deadline) -> dict:
        """스키마 위반이면 1회 재요청, 429면 Retry-After ≤ 2초이고 시간이 남을 때만 1회 재시도."""
        cap = self.config.tasks[task].cap_s
        for attempt in range(2):
            timeout = min(cap, deadline.left() - self.config.reserve_s)
            if timeout < p.min_timeout_s:
                raise _NoTime
            await self.usage.incr(self.today(), self._usage_key(p))
            try:
                return validate(await p.complete(prompt, schema, timeout), schema)
            except SchemaError:
                if attempt == 1:
                    raise
            except RateLimited as e:
                wait = e.retry_after
                if attempt == 1 or wait is None or wait > MAX_RETRY_AFTER_S:
                    raise
                if deadline.left() - wait - self.config.reserve_s < p.min_timeout_s:
                    raise
                await (self._sleep or asyncio.sleep)(wait)
        raise ProviderError("unreachable")
