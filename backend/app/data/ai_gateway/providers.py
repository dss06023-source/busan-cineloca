"""LLM 공급자. 공급자는 프롬프트와 스키마를 받아 JSON 객체 하나를 돌려주거나 ProviderError를 던진다."""

import asyncio
import re
from typing import Protocol

import httpx

from app.data.ai_gateway.config import ProviderConf
from app.data.ai_gateway.errors import ProviderError, ProviderTimeout, RateLimited
from app.data.ai_gateway.prompts import Prompt
from app.data.ai_gateway.schema import parse_json


class Provider(Protocol):
    name: str
    model: str
    min_timeout_s: float

    async def complete(self, prompt: Prompt, schema: dict, timeout_s: float) -> object: ...


def _retry_after(res: httpx.Response) -> float | None:
    if "retry-after" in res.headers:
        try:
            return float(res.headers["retry-after"])
        except ValueError:
            return None
    # Gemini는 오류 본문의 RetryInfo.retryDelay("2s")로 알려 준다
    m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', res.text)
    return float(m.group(1)) if m else None


async def _post(client: httpx.AsyncClient, url: str, timeout_s: float, **kw) -> dict:
    try:
        res = await client.post(url, timeout=httpx.Timeout(timeout_s), **kw)
    except httpx.TimeoutException:
        raise ProviderTimeout(url.split("?")[0]) from None
    except httpx.HTTPError as e:
        raise ProviderError(type(e).__name__) from None
    if res.status_code == 429:
        raise RateLimited(_retry_after(res))
    if res.status_code >= 400:
        raise ProviderError(f"HTTP {res.status_code}")
    try:
        return res.json()
    except ValueError:
        raise ProviderError("응답이 JSON이 아님") from None


class GeminiProvider:
    """Gemini API generateContent(REST). JSON 출력은 responseMimeType + responseJsonSchema.

    build-plan 6장은 Interactions API를 적었지만, 작업 환경에서 문서를 확인할 수 없어 안정 API로 만들었다
    (docs/deviations.md). 필드가 바뀌면 이 클래스만 고친다. temperature는 Gemini 3 권장대로 기본값을 둔다.
    """

    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, conf: ProviderConf, api_key: str, client: httpx.AsyncClient, model: str | None = None):
        self.model = model or conf.model
        self.min_timeout_s = conf.min_timeout_s
        self.thinking_level = conf.extra.get("thinking_level")
        self.api_key = api_key
        self.client = client

    async def complete(self, prompt: Prompt, schema: dict, timeout_s: float) -> object:
        config: dict = {"responseMimeType": "application/json", "responseJsonSchema": schema}
        if self.thinking_level:
            config["thinkingConfig"] = {"thinkingLevel": self.thinking_level}
        body = {
            "systemInstruction": {"parts": [{"text": prompt.system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
            "generationConfig": config,
        }
        data = await _post(
            self.client,
            f"{self.BASE}/models/{self.model}:generateContent",
            timeout_s,
            json=body,
            headers={"x-goog-api-key": self.api_key},
        )
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError("candidates 없음(차단 또는 빈 응답)") from None
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        return parse_json(text)


class OllamaProvider:
    """로컬 Ollama /api/chat. GPU PC가 있을 때만 설정으로 켠다."""

    name = "ollama"

    def __init__(self, conf: ProviderConf, base_url: str, client: httpx.AsyncClient):
        self.model = conf.model
        self.min_timeout_s = conf.min_timeout_s
        self.extra = conf.extra
        self.base_url = base_url.rstrip("/")
        self.client = client

    async def complete(self, prompt: Prompt, schema: dict, timeout_s: float) -> object:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}],
            "format": schema,
            "stream": False,
            "think": self.extra.get("think", False),
            "keep_alive": self.extra.get("keep_alive", "30m"),
            "options": self.extra.get("options", {}),
        }
        data = await _post(self.client, f"{self.base_url}/api/chat", timeout_s, json=body)
        try:
            return parse_json(data["message"]["content"])
        except (KeyError, TypeError):
            raise ProviderError("message 없음") from None


class FakeProvider:
    """테스트·E2E·장애 주입용(AI_PROVIDERS=fake). mode: ok|timeout|429|500|bad_schema"""

    name = "fake"
    model = "fake"
    min_timeout_s = 0.0

    def __init__(self, responses: dict[str, object] | None = None, mode: str = "ok", delay_s: float = 0.0):
        self.responses = responses or {}
        self.mode = mode
        self.delay_s = delay_s
        self.calls: list[str] = []

    async def complete(self, prompt: Prompt, schema: dict, timeout_s: float) -> object:
        self.calls.append(prompt.task)
        if self.delay_s:
            await asyncio.sleep(min(self.delay_s, timeout_s))
            if self.delay_s > timeout_s:
                raise ProviderTimeout("fake")
        match self.mode:
            case "timeout":
                raise ProviderTimeout("fake")
            case "429":
                raise RateLimited(30)
            case "500":
                raise ProviderError("HTTP 500")
            case "bad_schema":
                return {"unexpected": True}
        return self.responses.get(prompt.task, {})
