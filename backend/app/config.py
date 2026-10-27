"""
ResolveOps backend configuration.

Settings come from environment variables and the repository-root ``.env`` file
(see ``.env.example``). The ``.env`` file is also exported into ``os.environ`` so that
modules that read ``os.environ`` directly (gateway, mock services, Groq client) see
the same values.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"

# Real environment variables always win over the .env file.
load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # App
    environment: str = "development"
    version: str = "0.1.0"
    # Comma-separated list of browser origins allowed by CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Insert synthetic sample tickets and audit history on startup (reference data is always seeded)
    seed_demo_data: bool = True

    # Database
    database_url: str = "postgresql://resolveops:resolveops@localhost:5432/resolveops"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis (only probed by the health/readiness checks)
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Langfuse (optional; a local trace fallback is used when keys are empty)
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Groq LLM
    groq_api_key: str = ""
    groq_model_primary: str = "openai/gpt-oss-120b"
    groq_model_fast: str = "openai/gpt-oss-20b"
    groq_max_tokens: int = 4096
    groq_timeout_seconds: int = 30
    groq_max_retries: int = 3

    # Inbound webhook signing secrets (empty = unsigned requests accepted in development only)
    zendesk_webhook_secret: str = ""
    stripe_webhook_secret: str = ""

    # Mock system URLs
    mock_ticketing_url: str = "http://localhost:8001"
    mock_crm_url: str = "http://localhost:8002"
    mock_billing_url: str = "http://localhost:8003"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
