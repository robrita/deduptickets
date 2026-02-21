"""
Cluster request/response schemas.

DTOs for cluster API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from schemas.common import CamelCaseModel, PaginationMeta


class ClusterStatus(str, Enum):
    """Valid cluster statuses per OpenAPI spec."""

    CANDIDATE = "candidate"
    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ClusterMemberResponse(CamelCaseModel):
    """Response schema for a cluster member."""

    ticket_id: UUID
    ticket_number: str
    added_at: datetime
    summary: str | None = None
    category: str | None = None
    subcategory: str | None = None
    created_at: datetime | None = None
    confidence_score: float | None = None


class ClusterResponse(CamelCaseModel):
    """Response schema for a cluster."""

    id: UUID
    status: ClusterStatus
    summary: str
    ticket_count: int
    customer_id: str | None = None
    open_count: int = 0
    representative_ticket_id: UUID | None = None
    category: str | None = None
    subcategory: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    expires_at: datetime | None = None
    created_by: str | None = None
    dismissed_by: str | None = None
    dismissal_reason: str | None = None


class ClusterDetail(ClusterResponse):
    """Detailed cluster response with embedded members."""

    members: list[ClusterMemberResponse] = Field(default_factory=list)


class ClusterListResponse(CamelCaseModel):
    """Paginated list of clusters."""

    data: list[ClusterResponse]
    meta: PaginationMeta


class ClusterDismissRequest(CamelCaseModel):
    """Request to dismiss a cluster."""

    reason: str | None = Field(default=None, description="Optional reason for dismissal")
