"""
Common shared schemas for API responses.

Aligned with openapi.yaml components/schemas section.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(ge=0, description="Total number of items")
    offset: int = Field(ge=0, description="Current offset")
    limit: int = Field(ge=1, le=100, description="Items per page")
    has_more: bool = Field(description="Whether more items exist")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str = Field(description="Error code or type")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cosmos: str | None = Field(default=None, description="Cosmos DB connection status")
