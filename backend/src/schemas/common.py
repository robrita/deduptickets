"""
Common shared schemas for API responses.

Aligned with openapi.yaml components/schemas section.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """Base schema with camelCase JSON aliases.

    All API schemas inherit from this so that JSON input/output
    uses camelCase field names — matching Cosmos DB storage format
    and JavaScript conventions.

    ``populate_by_name=True`` allows internal code to use
    snake_case Python field names when constructing instances.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class PaginationMeta(CamelCaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(ge=0, description="Total number of items")
    offset: int = Field(ge=0, description="Current offset")
    limit: int = Field(ge=1, le=100, description="Items per page")
    has_more: bool = Field(description="Whether more items exist")


class ErrorResponse(CamelCaseModel):
    """Standard error response format."""

    error: str = Field(description="Error code or type")
    message: str = Field(description="Human-readable error message")
    details: dict | None = Field(default=None, description="Additional error details")


class HealthResponse(CamelCaseModel):
    """Health check response."""

    status: str = Field(default="healthy")
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cosmos: str | None = Field(default=None, description="Cosmos DB connection status")
