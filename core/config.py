from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    app_name: str = "Roundtable"
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="roundtable", alias="POSTGRES_DB")
    postgres_user: str = Field(default="roundtable", alias="POSTGRES_USER")
    postgres_password: str = Field(default="roundtablepwd", alias="POSTGRES_PASSWORD")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    secrets_key: str = Field(
        default="wQHiNnV3G1c2D5pW5uk3v8V4E7wH3qjzx9X6b0c1D2E=", alias="SECRETS_KEY"
    )

    max_rounds: int = Field(default=5, alias="MAX_ROUNDS")
    turn_timeout_sec: int = Field(default=60, alias="TURN_TIMEOUT_SEC")
    context_token_limit: int = Field(default=6000, alias="CONTEXT_TOKEN_LIMIT")
    payment_url: str = Field(default="https://pay.example.com/xyz", alias="PAYMENT_URL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-chat", alias="DEEPSEEK_MODEL")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    def celery_config(self) -> dict[str, Any]:
        return {
            "broker_url": self.redis_url,
            "result_backend": self.redis_url,
            "task_routes": {
                "worker.tasks.run_session": {"queue": "sessions"},
            },
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
