"""Application settings loaded from environment variables.

Uses pydantic-settings for typed configuration with fail-fast validation:
required Azure credentials must be present or the app refuses to start.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Azure Document Intelligence
    azure_doc_intelligence_endpoint: str = Field(
        ..., alias="AZURE_DOC_INTELLIGENCE_ENDPOINT"
    )
    azure_doc_intelligence_key: str = Field(..., alias="AZURE_DOC_INTELLIGENCE_KEY")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str = Field(..., alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(
        "2024-08-01-preview", alias="AZURE_OPENAI_API_VERSION"
    )

    # Confidence thresholds
    remediation_threshold: float = Field(0.80, alias="REMEDIATION_THRESHOLD")
    review_threshold: float = Field(0.60, alias="REVIEW_THRESHOLD")

    # Storage
    review_db_path: str = Field("./data/review.db", alias="REVIEW_DB_PATH")
    metrics_log_path: str = Field("./data/metrics.jsonl", alias="METRICS_LOG_PATH")

    # Cost model (USD)
    cost_di_per_page: float = Field(0.01, alias="COST_DI_PER_PAGE")
    cost_aoai_prompt_per_1k: float = Field(0.005, alias="COST_AOAI_PROMPT_PER_1K")
    cost_aoai_completion_per_1k: float = Field(
        0.015, alias="COST_AOAI_COMPLETION_PER_1K"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings. Raises pydantic ValidationError if required
    environment variables are missing - this is the fail-fast behavior."""
    return Settings()
