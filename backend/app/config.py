"""환경변수 설정. 값은 .env(infra/.env.example 참고)에서 읽고, 코드에는 기본값만 둔다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://app:app@localhost:5432/cineloca"
    notice_version: str = "2026-11-01"
    log_dir: str = "logs"
    ai_providers: str = "gemini"
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: str = ""
    ollama_url: str = ""  # 임베딩(bge-m3)
    ollama_llm_url: str = ""  # 로컬 LLM(선택). 비우면 체인에서 빠짐
    fake_ai_mode: str = "ok"  # AI_PROVIDERS=fake일 때 ok|timeout|429|500|bad_schema
    # 세션당 AI 요청 분당 한도(AI-REQ-15, ERR-011)
    ai_rate_per_min: int = 5
    # 스탬프·배지 토큰 서명 키 "kid:비밀,kid:비밀"(앞의 것으로 서명). 비우면 실행할 때마다 임시 키(개발용)
    token_keys: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
