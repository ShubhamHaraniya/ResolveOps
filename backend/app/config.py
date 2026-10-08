"""
ResolveOps Backend Configuration
All settings loaded from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    version: str = "0.1.0"

    # Database
    database_url: str = "postgresql://resolveops:resolveops@localhost:5432/resolveops"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "resolveops_policies"

    # Langfuse
    langfuse_host: str = "http://localhost:3100"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Groq LLM
    groq_api_key: str = ""
    groq_model_primary: str = "openai/gpt-oss-120b"
    groq_model_fast: str = "openai/gpt-oss-20b"
    groq_max_tokens: int = 4096
    groq_timeout_seconds: int = 30
    groq_max_retries: int = 3

    # Mock system URLs
    mock_ticketing_url: str = "http://localhost:8001"
    mock_crm_url: str = "http://localhost:8002"
    mock_billing_url: str = "http://localhost:8003"
    mock_iam_url: str = "http://localhost:8004"

    # Rate / Budget limits
    max_tool_calls_per_run: int = 20
    max_llm_calls_per_run: int = 10
    max_replans_per_run: int = 2

    # RAG
    embedding_model: str = "BAAI/bge-m3"
    embedding_fallback_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 20
    rag_rerank_top_n: int = 5

    # Billing mock simulation
    billing_error_rate: float = 0.1
    billing_timeout_simulation: bool = False

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
