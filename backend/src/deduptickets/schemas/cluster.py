"""
Cluster request/response schemas.

DTOs for cluster API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from deduptickets.schemas.common import PaginationMeta
    from deduptickets.schemas.ticket import TicketResponse


class ClusterStatus(str, Enum):
    """Valid cluster statuses per OpenAPI spec."""

    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ConfidenceLevel(str, Enum):
    """Cluster confidence levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchingSignals(BaseModel):
    """Signals indicating why tickets were grouped."""

    exact_matches: list[dict[str, str]] = Field(default_factory=list)
    time_window: dict[str, datetime] | None = None
    text_similarity: dict[str, Any] | None = None
    field_matches: list[dict[str, str]] = Field(default_factory=list)


class ClusterResponse(BaseModel):
    """Response schema for a cluster."""

    id: UUID
    status: ClusterStatus
    confidence: ConfidenceLevel
    summary: str
    matching_signals: MatchingSignals | None = None
    primary_ticket_id: UUID | None = None
    ticket_count: int
    created_at: datetime
    updated_at: datetime | None = None
    expires_at: datetime | None = None
    created_by: str | None = None


class ClusterDetail(ClusterResponse):
    """Detailed cluster response with member tickets."""

    tickets: list[TicketResponse] = Field(default_factory=list)


class ClusterListResponse(BaseModel):
    """Paginated list of clusters."""

    data: list[ClusterResponse]
    meta: PaginationMeta


class ClusterDismissRequest(BaseModel):
    """Request to dismiss a cluster."""

    reason: str | None = Field(default=None, description="Optional reason for dismissal")
