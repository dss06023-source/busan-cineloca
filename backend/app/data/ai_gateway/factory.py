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


# AI_PROVIDERS=fake일 때 작업별 고정 응답(E2E·장애 주입). 미니 시드(가짜 데이터)의 시연 장면 2~4에 맞춘 값이다.
# 입력과 상관없이 같은 값을 돌려주므로, 다른 작품·질의에서는 근거 대조가 걸러 강등되는 것이 정상이다
FAKE_RESPONSES: dict[str, dict] = {
    # 장면 3: "강도윤 나온 영화 촬영지 중 지하철역에서 걸어서 10분 안"
    "extract_query": {
        "persons": ["강도윤"],
        "base": {"kind": "station"},
        "travel": {"mode": "walk", "minutes": 10},
        "result_type": "LOCATION",
        "out_of_scope": False,
    },
    "summarize_results": {
        "sentences": [
            {"text": "강도윤 출연작의 촬영지를 역에서 걷기 좋은 곳 위주로 모았습니다.", "entities": ["강도윤"]}
        ]
    },
    # 장면 4: 서면 출발 반나절
    "structure_preference": {"start": "서면", "budget_h": 4, "mood_tags": ["야경"], "out_of_scope": False},
    "course_intro": {
        "title": "서면에서 출발하는 촬영지 반나절",
        "sentences": [{"text": "서면에서 출발해 촬영지를 차례로 둘러보는 반나절 코스입니다.", "entities": ["서면"]}],
        "reasons": [],
    },
    # 장면 2: 「부산 추격전」(작품 3)
    "work_intro": {
        "sentences": [
            {"text": "「부산 추격전」은 2017년에 나온 범죄 액션 영화입니다.", "entities": ["부산 추격전", "2017"]},
            {"text": "형사 강도윤이 부산역에서 사라진 증인을 쫓습니다.", "entities": ["강도윤", "부산역"]},
        ]
    },
    "suggest_tags": {"tags": [], "confidence": 0.0},
    "judge_match": {"kmdb_id": None, "confidence": 0.0},
}
