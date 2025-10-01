from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl


class Settings(BaseSettings):
    telegram_bot_token: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "roundtable"
    postgres_user: str = "roundtable"
    postgres_password: str = "roundtablepwd"
    redis_url: str = "redis://redis:6379/0"
    secrets_key: str
    max_rounds: int = 5
    turn_timeout_sec: int = 60
    context_token_limit: int = 6000
    session_tokens_in_limit: int = 60000
    session_tokens_out_limit: int = 60000
    session_cost_limit: float = 100.0
    payment_url: AnyHttpUrl
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    deepseek_api_key: str
    deepseek_model: str = "deepseek-chat"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
