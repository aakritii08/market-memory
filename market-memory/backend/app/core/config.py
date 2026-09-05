from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Market Memory"
    database_url: str = "postgresql+psycopg://market:market@db:5432/market_memory"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change-me-in-production"
    jwt_exp_minutes: int = 60 * 24
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-5-mini"
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]

        if value.startswith("postgresql://"):
            value = value.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()