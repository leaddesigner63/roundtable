from __future__ import annotations

from functools import lru_cache
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    telegram_bot_token: str = Field(default="test-token")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "roundtable"
    postgres_user: str = "roundtable"
    postgres_password: str = "roundtablepwd"

    redis_url: str = "redis://localhost:6379/0"

    secrets_key: str = Field(default_factory=lambda: Fernet.generate_key().decode())

    max_rounds: int = 5
    turn_timeout_sec: int = 60
    context_token_limit: int = 6000
    payment_url: str = "https://example.com/pay"

    openai_api_key: str | None = None
    openai_model: str | None = None

    deepseek_api_key: str | None = None
    deepseek_model: str | None = None

    environment: Literal["dev", "test", "prod"] = "dev"

    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
