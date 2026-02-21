"""
Merge request/response schemas.

DTOs for merge API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field

from schemas.common import CamelCaseModel, PaginationMeta


class MergeBehavior(str, Enum):
    """Merge behavior options per OpenAPI spec."""

    KEEP_LATEST = "keep_latest"
    COMBINE_NOTES = "combine_notes"
    RETAIN_ALL = "retain_all"


class MergeStatus(str, Enum):
    """Merge operation statuses."""

    PENDING = "pending"
    COMPLETED = "completed"
    REVERTED = "reverted"


class MergeRequest(CamelCaseModel):
    """Request schema to merge a cluster."""

    cluster_id: UUID = Field(description="Source cluster to merge")
    primary_ticket_id: UUID = Field(description="Ticket to keep as primary")
    merge_behavior: MergeBehavior = Field(description="How to handle merged ticket data")


class MergeResponse(CamelCaseModel):
    """Response schema for a merge operation."""

    id: UUID
    cluster_id: UUID
    primary_ticket_id: UUID
    secondary_ticket_ids: list[UUID]
    merge_behavior: MergeBehavior
    status: MergeStatus
    performed_by: str
    performed_at: datetime
    reverted_at: datetime | None = None
    reverted_by: str | None = None
    revert_reason: str | None = None


class MergeListResponse(CamelCaseModel):
    """Paginated list of merge operations."""

    data: list[MergeResponse]
    meta: PaginationMeta


class RevertRequest(CamelCaseModel):
    """Request to revert a merge."""

    reason: str | None = Field(default=None, description="Reason for reverting")


class RevertConflict(CamelCaseModel):
    """A single conflict in a revert operation."""

    ticket_id: UUID
    field: str
    original_value: str | None = None
    current_value: str | None = None


class RevertConflictResponse(CamelCaseModel):
    """Response when revert conflicts are detected."""

    error: str
    message: str
    conflicts: list[RevertConflict] = Field(default_factory=list)
