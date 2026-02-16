from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Friction Finder API"
    environment: str = "dev"
    database_url: str = "sqlite:///./friction_finder.db"
    app_password: str = "changeme"

    ai_provider: Literal["none", "openai", "ollama"] = "none"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str | None = None
    model_name: str = "gpt-4o-mini"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    report_quickwin_impact_threshold_hours: float = 5.0

    # Webhook security
    vapi_webhook_secret: str | None = None
    n8n_webhook_secret: str | None = None
    n8n_webhook_url: str | None = None

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
