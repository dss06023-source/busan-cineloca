"""WP-06 완료 조건: 장애 4종(시간 초과·429·5xx·스키마 위반), 7.5초 마감, 캐시·호출 수·차단기."""

from datetime import date

import pytest

from app.data.ai_gateway.config import load_config
from app.data.ai_gateway.deadline import Deadline
from app.data.ai_gateway.errors import AIUnavailable, ProviderError, ProviderTimeout, RateLimited
from app.data.ai_gateway.gateway import LLMClient, cache_key
from app.data.ai_gateway.providers import FakeProvider

CONFIG = load_config()
OK = {"result_type": "LOCATION", "out_of_scope": False, "districts": ["해운대구"]}


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class MemCache:
    def __init__(self):
        self.d = {}

    async def get(self, key):
        return self.d.get(key)

    async def put(self, key, task, value, ttl_h=24):
        self.d[key] = value


class MemUsage:
    def __init__(self):
        self.d = {}

    async def incr(self, day, key, by=1):
        self.d[(day, key)] = self.d.get((day, key), 0) + by
        return self.d[(day, key)]

    async def get(self, day, key):
        return self.d.get((day, key), 0)


class Scripted:
    """정해 둔 결과를 차례로 내고, 부를 때마다 가짜 시계를 cost초 앞으로 민다."""

    def __init__(self, name, clock, outcomes, cost=0.5, model="m", min_timeout_s=1.0):
        self.name, self.model, self.min_timeout_s = name, model, min_timeout_s
        self.clock, self.outcomes, self.cost = clock, list(outcomes), cost
        self.timeouts: list[float] = []

    async def complete(self, prompt, schema, timeout_s):
        self.timeouts.append(timeout_s)
        out = self.outcomes.pop(0) if self.outcomes else OK
        if isinstance(out, ProviderTimeout):
            self.clock.t += timeout_s  # 시간 초과는 제한 시간을 다 쓴다
            raise out
        self.clock.t += self.cost
        if isinstance(out, Exception):
            raise out
        return out


def make(providers, usage=None, cache=None):
    slept = []

    async def sleep(s):
        slept.append(s)

    client = LLMClient(
        CONFIG,
        {p.name: p for p in providers},
        cache or MemCache(),
        usage or MemUsage(),
        today=lambda: date(2026, 11, 1),
        sleep=sleep,
    )
    client.slept = slept
    return client


async def test_ok_and_cache_hit():
    clock = Clock()
    g = Scripted("gemini", clock, [OK])
    client = make([g])
    r = await client.generate("extract_query", {"user_input": "해운대"}, Deadline(7.5, clock))
    assert r.data == OK and r.provider == "gemini" and not r.cached
    r2 = await client.generate("extract_query", {"user_input": "해운대"}, Deadline(7.5, clock))
    assert r2.cached and r2.provider == "cache" and len(g.timeouts) == 1


def test_cache_key_changes_with_version_and_input():
    a = cache_key("extract_query", "v1", {"q": "a"}, {})
    assert a != cache_key("extract_query", "v2", {"q": "a"}, {})
    assert a != cache_key("extract_query", "v1", {"q": "b"}, {})
    assert a == cache_key("extract_query", "v1", {"q": "a"}, {})


@pytest.mark.parametrize("mode", ["timeout", "429", "500", "bad_schema"])
async def test_four_failure_modes_raise_ai_unavailable(mode):
    """FakeProvider 장애 4종은 모두 AIUnavailable로 끝나고, 실패 응답은 캐시하지 않는다."""
    cache = MemCache()
    client = make([FakeProvider(mode=mode)], cache=cache)
    for _ in range(10):  # 장애 주입 시험: 각 10회
        with pytest.raises(AIUnavailable):
            await client.generate("extract_query", {"user_input": "x"}, Deadline(7.5))
    assert cache.d == {}


async def test_falls_back_to_next_provider():
    clock = Clock()
    g = Scripted("gemini", clock, [ProviderError("HTTP 500")])
    o = Scripted("ollama", clock, [OK], min_timeout_s=2.0)
    r = await make([g, o]).generate("extract_query", {}, Deadline(7.5, clock))
    assert r.provider == "ollama"


async def test_deadline_7_5s_skips_provider_without_time():
    """첫 공급자가 시간을 다 쓰고 실패하면 다음 공급자를 부르지 않고 마감 안에 강등한다."""
    clock = Clock()
    g = Scripted("gemini", clock, [ProviderTimeout("x")])
    o = Scripted("ollama", clock, [OK], min_timeout_s=2.0)
    deadline = Deadline(7.5, clock)
    clock.t += 4.0  # 앞 단계(조건 추출 등)가 4초를 씀
    with pytest.raises(AIUnavailable) as e:
        await make([g, o]).generate("summarize_results", {}, deadline)
    assert g.timeouts == [pytest.approx(3.2)]  # min(상한 4.0, 남은 3.5 − 0.3)
    assert o.timeouts == []
    assert "ollama:no_time" in e.value.reasons
    assert clock.t - (deadline.at - 7.5) <= 7.5


async def test_no_call_when_less_than_min_timeout_left():
    clock = Clock()
    g = Scripted("gemini", clock, [OK])
    deadline = Deadline(7.5, clock)
    clock.t += 6.3  # 남은 1.2초 − 0.3 = 0.9 < Gemini 최소 1.0
    with pytest.raises(AIUnavailable):
        await make([g]).generate("extract_query", {}, deadline)
    assert g.timeouts == []


async def test_schema_violation_retries_once():
    clock = Clock()
    g = Scripted("gemini", clock, [{"bad": 1}, OK])
    r = await make([g]).generate("extract_query", {}, Deadline(7.5, clock))
    assert r.data == OK and len(g.timeouts) == 2


async def test_schema_violation_twice_fails():
    clock = Clock()
    g = Scripted("gemini", clock, [{"bad": 1}, {"bad": 2}, OK])
    with pytest.raises(AIUnavailable):
        await make([g]).generate("extract_query", {}, Deadline(7.5, clock))
    assert len(g.timeouts) == 2


async def test_429_short_retry_after_retries_once():
    clock = Clock()
    g = Scripted("gemini", clock, [RateLimited(1.0), OK])
    client = make([g])
    r = await client.generate("extract_query", {}, Deadline(7.5, clock))
    assert r.data == OK and client.slept == [1.0]


async def test_429_long_retry_after_gives_up():
    clock = Clock()
    g = Scripted("gemini", clock, [RateLimited(30), OK])
    client = make([g])
    with pytest.raises(AIUnavailable):
        await client.generate("extract_query", {}, Deadline(7.5, clock))
    assert client.slept == [] and len(g.timeouts) == 1


async def test_daily_quota_skips_gemini_and_counts_by_model():
    clock = Clock()
    usage = MemUsage()
    day = date(2026, 11, 1)
    g = Scripted("gemini", clock, [OK], model="gemini-3.5-flash-lite")
    client = make([g], usage=usage)
    await client.generate("extract_query", {"n": 1}, Deadline(7.5, clock))
    assert usage.d[(day, "gemini:gemini-3.5-flash-lite")] == 1
    usage.d[(day, "gemini:gemini-3.5-flash-lite")] = CONFIG.providers["gemini"].daily_limit
    with pytest.raises(AIUnavailable) as e:
        await client.generate("extract_query", {"n": 2}, Deadline(7.5, clock))
    assert e.value.reasons == ["gemini:daily_limit"]


async def test_breaker_opens_after_consecutive_failures():
    client = make([FakeProvider(mode="500")])
    for _ in range(CONFIG.breaker_fails):
        with pytest.raises(AIUnavailable):
            await client.generate("extract_query", {}, Deadline(7.5))
    assert client.breaker_states() == {"fake": "open"}
    with pytest.raises(AIUnavailable) as e:
        await client.generate("extract_query", {}, Deadline(7.5))
    assert e.value.reasons == ["fake:breaker_open"]


async def test_chain_order_from_config():
    clock = Clock()
    g = Scripted("gemini", clock, [OK])
    o = Scripted("ollama", clock, [{"tags": ["바다"], "confidence": 0.7}], min_timeout_s=2.0)
    r = await make([g, o]).generate("suggest_tags", {}, Deadline(60, clock))
    assert r.provider == "ollama" and g.timeouts == []  # suggest_tags는 ollama 먼저


async def test_fake_only_chain_and_task_response():
    fake = FakeProvider({"extract_query": OK})
    r = await make([fake]).generate("extract_query", {}, Deadline(7.5))
    assert r.provider == "fake" and r.data == OK and fake.calls == ["extract_query"]
