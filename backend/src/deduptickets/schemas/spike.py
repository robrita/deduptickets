"""
Spike request/response schemas.

DTOs for spike API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from deduptickets.schemas.cluster import ClusterResponse
    from deduptickets.schemas.common import PaginationMeta


class SpikeStatus(str, Enum):
    """Spike alert statuses per OpenAPI spec."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class SeverityLevel(str, Enum):
    """Spike severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SpikeResponse(BaseModel):
    """Response schema for a spike alert."""

    id: UUID
    status: SpikeStatus
    severity: SeverityLevel
    field_name: str
    field_value: str
    current_count: int
    baseline_count: float
    percentage_increase: float
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    detected_at: datetime
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class SpikeDetail(SpikeResponse):
    """Detailed spike response with affected clusters."""

    affected_clusters: list[ClusterResponse] = Field(default_factory=list)


class SpikeListResponse(BaseModel):
    """Paginated list of spike alerts."""

    data: list[SpikeResponse]
    meta: PaginationMeta


class SpikeAcknowledgeRequest(BaseModel):
    """Request to acknowledge a spike."""

    pass  # No body required, user taken from auth


class SpikeResolveRequest(BaseModel):
    """Request to resolve a spike."""

    pass  # No body required, user taken from auth
