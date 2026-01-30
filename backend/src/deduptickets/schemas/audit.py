"""
Audit request/response schemas.

DTOs for audit API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from deduptickets.schemas.common import PaginationMeta


class AuditActionType(str, Enum):
    """Valid audit action types per OpenAPI spec."""

    MERGE = "merge"
    REVERT = "revert"
    CLUSTER_CREATE = "cluster_create"
    CLUSTER_DISMISS = "cluster_dismiss"
    CLUSTER_MEMBER_REMOVE = "cluster_member_remove"
    TICKET_CREATE = "ticket_create"
    TICKET_UPDATE = "ticket_update"
    SPIKE_DETECT = "spike_detect"
    SPIKE_ACKNOWLEDGE = "spike_acknowledge"
    SPIKE_RESOLVE = "spike_resolve"


class ActorType(str, Enum):
    """Actor types."""

    USER = "user"
    SYSTEM = "system"


class AuditOutcome(str, Enum):
    """Audit outcome values."""

    SUCCESS = "success"
    FAILURE = "failure"


class AuditResponse(BaseModel):
    """Response schema for an audit entry."""

    id: UUID
    action_type: AuditActionType
    actor_id: str
    actor_type: ActorType
    resource_type: str
    resource_id: UUID
    related_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: AuditOutcome
    error_message: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditListResponse(BaseModel):
    """Paginated list of audit entries."""

    data: list[AuditResponse]
    meta: PaginationMeta


class AuditSearchParams(BaseModel):
    """Query parameters for audit search."""

    action_type: AuditActionType | None = None
    actor_id: str | None = None
    resource_type: str | None = None
    resource_id: UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
