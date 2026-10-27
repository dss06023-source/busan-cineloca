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
    # 세션당 AI 요청 분당 한도(AI-REQ-15, ERR-011)
    ai_rate_per_min: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()
