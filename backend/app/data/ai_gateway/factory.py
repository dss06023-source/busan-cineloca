"""설정으로 LLMClient와 Embedder를 만든다. 키가 없거나 꺼진 공급자는 체인에서 빠진다."""

import logging
from dataclasses import replace

import httpx
from psycopg_pool import AsyncConnectionPool

from app.data.ai_gateway.config import AIConfig, load_config
from app.data.ai_gateway.embedder import FakeEmbedder, OllamaEmbedder
from app.data.ai_gateway.gateway import LLMClient
from app.data.ai_gateway.providers import FakeProvider, GeminiProvider, OllamaProvider, Provider
from app.data.repositories.ai_cache import AICacheRepository
from app.data.repositories.usage import UsageRepository

log = logging.getLogger(__name__)


def build_providers(
    config: AIConfig,
    names: list[str],
    client: httpx.AsyncClient,
    gemini_api_key: str = "",
    gemini_model: str = "",
    ollama_llm_url: str = "",
    fake_mode: str = "ok",
    fake_responses: dict | None = None,
) -> dict[str, Provider]:
    providers: dict[str, Provider] = {}
    if "fake" in names:
        providers["fake"] = FakeProvider(fake_responses, mode=fake_mode)
    if "gemini" in names:
        if gemini_api_key:
            providers["gemini"] = GeminiProvider(
                config.providers["gemini"], gemini_api_key, client, gemini_model or None
            )
        else:
            log.warning("GEMINI_API_KEY가 없어 Gemini를 체인에서 뺍니다")
    if "ollama" in names and ollama_llm_url:
        conf = replace(config.providers["ollama"], enabled=True)
        providers["ollama"] = OllamaProvider(conf, ollama_llm_url, client)
    return providers


def build_llm_client(settings, pool: AsyncConnectionPool, client: httpx.AsyncClient) -> LLMClient:
    config = load_config()
    names = [n.strip() for n in settings.ai_providers.split(",") if n.strip()]
    providers = build_providers(
        config,
        names,
        client,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        ollama_llm_url=settings.ollama_llm_url,
        fake_mode=settings.fake_ai_mode,
        fake_responses=FAKE_RESPONSES,
    )
    return LLMClient(config, providers, AICacheRepository(pool), UsageRepository(pool))


def build_embedder(settings, client: httpx.AsyncClient):
    config = load_config()
    if "fake" in settings.ai_providers or not settings.ollama_url:
        return FakeEmbedder(config.embedder["dim"])
    e = config.embedder
    return OllamaEmbedder(settings.ollama_url, client, model=e["model"], timeout_s=e["timeout_s"])


# AI_PROVIDERS=fake일 때 작업별 고정 응답(E2E·장애 주입). 기능 WP가 시연 장면에 맞게 늘린다
FAKE_RESPONSES: dict[str, dict] = {
    "extract_query": {"result_type": "LOCATION", "out_of_scope": False},
    "summarize_results": {"sentences": []},
    "structure_preference": {"budget_h": 4, "out_of_scope": False},
    "course_intro": {"title": "추천 코스", "sentences": [], "reasons": []},
    "work_intro": {"sentences": []},
    "suggest_tags": {"tags": [], "confidence": 0.0},
    "judge_match": {"kmdb_id": None, "confidence": 0.0},
}
