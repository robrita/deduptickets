"""
Ticket request/response schemas.

DTOs for ticket API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from deduptickets.schemas.common import PaginationMeta


class TicketStatus(str, Enum):
    """Valid ticket statuses per OpenAPI spec."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    MERGED = "merged"


class TicketPriority(str, Enum):
    """Ticket priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketSeverity(str, Enum):
    """Issue severity levels."""

    S1 = "s1"
    S2 = "s2"
    S3 = "s3"
    S4 = "s4"


class TicketChannel(str, Enum):
    """Support channels."""

    IN_APP = "in_app"
    CHAT = "chat"
    EMAIL = "email"
    SOCIAL = "social"
    PHONE = "phone"


class TicketCreate(BaseModel):
    """Request schema for creating/ingesting a ticket."""

    ticket_number: str = Field(max_length=50, description="External ticket ID from source system")
    customer_id: str | None = Field(default=None, max_length=100, description="Customer identifier")
    summary: str = Field(max_length=500, description="Brief issue description")
    description: str | None = Field(default=None, description="Detailed issue description")
    status: TicketStatus = Field(description="Ticket status")
    priority: TicketPriority | None = Field(default=None, description="Ticket priority")
    severity: TicketSeverity | None = Field(default=None, description="Issue severity level")
    channel: TicketChannel = Field(description="Support channel")
    category: str = Field(max_length=100, description="Issue category")
    subcategory: str | None = Field(default=None, max_length=100, description="Issue subcategory")
    region: str = Field(max_length=100, description="Geographic region")
    city: str | None = Field(default=None, max_length=100, description="City name")
    transaction_id: str | None = Field(
        default=None, max_length=100, description="Related transaction ID"
    )
    amount: float | None = Field(default=None, description="Transaction amount")
    currency: str | None = Field(
        default=None, max_length=10, description="Currency code (PHP, USD, etc.)"
    )
    merchant: str | None = Field(default=None, max_length=255, description="Bank or merchant name")
    occurred_at: datetime | None = Field(default=None, description="When the issue occurred")
    created_at: datetime = Field(description="When ticket was created")
    raw_metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class TicketResponse(BaseModel):
    """Response schema for a ticket."""

    id: UUID
    ticket_number: str
    customer_id: str | None = None
    summary: str
    description: str | None = None
    status: TicketStatus
    priority: TicketPriority | None = None
    severity: TicketSeverity | None = None
    channel: TicketChannel
    category: str
    subcategory: str | None = None
    region: str
    city: str | None = None
    transaction_id: str | None = None
    amount: float | None = None
    currency: str | None = None
    merchant: str | None = None
    occurred_at: datetime | None = None
    cluster_id: UUID | None = None
    merged_into_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""

    data: list[TicketResponse]
    meta: PaginationMeta
