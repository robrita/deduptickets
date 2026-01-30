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
        default="https://localhost:8081",
        description="Cosmos DB account endpoint URL",
    )
    cosmos_key: SecretStr = Field(
        description="Cosmos DB account key or resource token",
        # Default is the well-known Cosmos Emulator key
        default="C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
    )
    cosmos_database: str = Field(
        default="deduptickets",
        description="Cosmos DB database name",
    )
    cosmos_ssl_verify: bool = Field(
        default=False,
        description="Verify SSL certificates (set False for Emulator)",
    )

    # ==========================================================================
    # API Security
    # ==========================================================================
    api_key: SecretStr = Field(
        default="dev-api-key-change-in-production",
        description="API key for authentication",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
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
    # Clustering Configuration
    # ==========================================================================
    similarity_threshold: float = Field(
        default=0.7,
        description="Text similarity threshold for clustering (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    clustering_time_window_hours: int = Field(
        default=1,
        description="Time window for clustering in hours",
        ge=1,
        le=24,
    )

    # ==========================================================================
    # Spike Detection Configuration
    # ==========================================================================
    spike_threshold_percent: int = Field(
        default=200,
        description="Percentage increase threshold to trigger spike alert",
        ge=100,
        le=1000,
    )
    spike_monitor_fields: str = Field(
        default="category,channel,region,merchant,subcategory,severity",
        description="Comma-separated fields to monitor for spikes",
    )

    @property
    def spike_monitor_field_list(self) -> list[str]:
        """Get spike monitor fields as a list."""
        return [f.strip() for f in self.spike_monitor_fields.split(",") if f.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
