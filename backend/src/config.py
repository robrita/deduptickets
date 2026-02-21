"""
Application configuration using pydantic-settings.

All configuration is loaded from environment variables with sensible defaults
for local development.

Constitution Compliance:
- Principle I: Security-First - Secrets use SecretStr, no hardcoded values
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Azure Cosmos DB Configuration
    # ==========================================================================
    cosmos_endpoint: str = Field(
        description="Cosmos DB account endpoint URL (required)",
    )
    cosmos_use_aad: bool = Field(
        default=False,
        description="Use Microsoft Entra ID (AAD) auth instead of account key",
    )
    cosmos_key: SecretStr | None = Field(
        default=None,
        description="Cosmos DB account key (required when COSMOS_USE_AAD=false)",
    )
    cosmos_database: str = Field(
        description="Cosmos DB database name (required)",
    )
    cosmos_ssl_verify: bool = Field(
        default=False,
        description="Verify SSL certificates (set False for Emulator)",
    )

    # ==========================================================================
    # API Security
    # ==========================================================================
    api_key: SecretStr = Field(
        default=SecretStr("dev-api-key-change-in-production"),
        description="API key for authentication",
    )
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:7071",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        description="Allowed CORS origins",
    )

    # ==========================================================================
    # Application Settings
    # ==========================================================================
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300,
    )

    # ==========================================================================
    # Azure OpenAI Configuration
    # ==========================================================================
    azure_openai_endpoint: str = Field(
        description="Azure OpenAI endpoint URL (required)",
    )
    azure_openai_use_aad: bool = Field(
        default=True,
        description="Use Entra ID (AAD) auth for Azure OpenAI; when False, uses API key",
    )
    azure_openai_key: SecretStr | None = Field(
        default=None,
        description="Azure OpenAI API key (required when AZURE_OPENAI_USE_AAD=false)",
    )
    azure_openai_api_version: str = Field(
        default="2024-10-21",
        description="Azure OpenAI API version",
    )
    azure_openai_embedding_deployment: str = Field(
        description="Azure OpenAI embedding model deployment name (required)",
    )
    azure_openai_embedding_dimensions: int = Field(
        default=1536,
        description="Embedding vector dimensions",
        ge=1,
        le=4096,
    )

    # ==========================================================================
    # Cluster-First Dedup Configuration
    # ==========================================================================
    cluster_auto_threshold: float = Field(
        default=0.92,
        description="Auto-assign threshold (>= this = auto)",
        ge=0.0,
        le=1.0,
    )
    cluster_review_threshold: float = Field(
        default=0.85,
        description="Review threshold (>= this and < auto = review)",
        ge=0.0,
        le=1.0,
    )
    cluster_max_members: int = Field(
        default=100,
        description="Max member tickets per cluster (capacity cap for 2 MB Cosmos item limit)",
        ge=2,
        le=2000,
    )
    cluster_top_k: int = Field(
        default=10,
        description="Max cluster candidates from vector search",
        ge=1,
        le=50,
    )
    dedup_window_days: int = Field(
        default=14,
        description="Time window for dedup candidate search in days",
        ge=1,
        le=365,
    )
    cluster_search_months: int = Field(
        default=2,
        description="Number of months to search (current + N-1 previous)",
        ge=1,
        le=12,
    )
    dedup_filter_by_customer: bool = Field(
        default=False,
        description="Filter cluster candidates by customerId",
    )
    dedup_weight_semantic: float = Field(
        default=0.85,
        description="Weight for semantic similarity signal in confidence scoring",
        ge=0.0,
        le=1.0,
    )
    dedup_weight_subcategory: float = Field(
        default=0.10,
        description="Weight for subcategory match signal in confidence scoring",
        ge=0.0,
        le=1.0,
    )
    dedup_weight_category: float = Field(
        default=0.03,
        description="Weight for category match signal in confidence scoring",
        ge=0.0,
        le=1.0,
    )
    dedup_weight_time: float = Field(
        default=0.02,
        description="Weight for time proximity signal in confidence scoring",
        ge=0.0,
        le=1.0,
    )
    dedup_open_statuses: list[str] = Field(
        default=["open", "pending"],
        description="Ticket statuses considered open for dedup",
    )

    # ==========================================================================
    # Proxy / External Ingestion
    # ==========================================================================
    proxy_tickets_endpoint: str | None = Field(
        default=None,
        description="Optional proxy URL for ticket ingestion; bypasses /api/v1/tickets when set",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings populates from env vars
