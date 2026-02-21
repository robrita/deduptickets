"""
Ticket request/response schemas.

DTOs for ticket API endpoints aligned with openapi.yaml.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from schemas.common import CamelCaseModel, PaginationMeta


class TicketStatus(str, Enum):
    """Valid ticket statuses per OpenAPI spec."""

    OPEN = "open"
    PENDING = "pending"
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

    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"


class TicketChannel(str, Enum):
    """Support channels."""

    IN_APP = "InApp"
    CHAT = "Chat"
    EMAIL = "Email"
    SOCIAL = "Social"
    PHONE = "Phone"


class TicketCreate(CamelCaseModel):
    """Request schema for creating/ingesting a ticket."""

    ticket_number: str = Field(max_length=50, description="External ticket ID from source system")
    customer_id: str | None = Field(default=None, max_length=100, description="Customer identifier")
    name: str | None = Field(default=None, max_length=255, description="Customer display name")
    mobile_number: str | None = Field(default=None, max_length=20, description="Phone number")
    email: str | None = Field(default=None, max_length=255, description="Email address")
    account_type: str | None = Field(
        default=None, max_length=50, description="Verified, Basic, etc"
    )
    summary: str = Field(max_length=500, description="Brief issue description")
    description: str | None = Field(default=None, description="Detailed issue description")
    status: TicketStatus = Field(description="Ticket status")
    priority: TicketPriority | None = Field(default=None, description="Ticket priority")
    severity: TicketSeverity | None = Field(default=None, description="Issue severity level")
    channel: TicketChannel = Field(description="Support channel")
    category: str = Field(max_length=100, description="Issue category")
    subcategory: str | None = Field(default=None, max_length=100, description="Issue subcategory")
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


class TicketResponse(CamelCaseModel):
    """Response schema for a ticket."""

    id: UUID
    ticket_number: str
    customer_id: str | None = None
    name: str | None = None
    mobile_number: str | None = None
    email: str | None = None
    account_type: str | None = None
    summary: str
    description: str | None = None
    status: TicketStatus
    priority: TicketPriority | None = None
    severity: TicketSeverity | None = None
    channel: TicketChannel
    category: str
    subcategory: str | None = None
    transaction_id: str | None = None
    amount: float | None = None
    currency: str | None = None
    merchant: str | None = None
    occurred_at: datetime | None = None
    cluster_id: UUID | None = None
    merged_into_id: UUID | None = None
    dedup_decision: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None


class TicketListResponse(CamelCaseModel):
    """Paginated list of tickets."""

    data: list[TicketResponse]
    meta: PaginationMeta
