"""
Ticket domain model.

Represents a support ticket ingested from the source ticketing system.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TicketStatus(StrEnum):
    """Ticket status enumeration."""

    OPEN = "open"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"
    MERGED = "merged"


class TicketPriority(StrEnum):
    """Ticket priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Ticket(BaseModel):
    """
    Ticket entity representing a support ticket.

    Aligned with data-model.md tickets container schema.
    """

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Unique document identifier")
    pk: str = Field(description="Partition key: {region}|{year-month}")

    # External reference
    ticket_number: str = Field(max_length=50, description="External ticket ID from source system")

    # Timestamps (ISO 8601)
    created_at: datetime = Field(description="When ticket was created")
    updated_at: datetime = Field(description="Last modification timestamp")
    closed_at: datetime | None = Field(default=None, description="When ticket was closed")

    # Status and priority
    status: TicketStatus = Field(default=TicketStatus.OPEN, description="Ticket status")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="Ticket priority")
    severity: str | None = Field(default=None, max_length=10, description="S1, S2, S3, S4")
    channel: str = Field(max_length=50, description="InApp, Chat, Email, Social, Phone")

    # Customer information (masked in API responses)
    customer_id: str = Field(max_length=100, description="Customer identifier")
    name: str | None = Field(default=None, max_length=255, description="Customer display name")
    mobile_number: str | None = Field(default=None, max_length=20, description="Phone number")
    email: str | None = Field(default=None, max_length=255, description="Email address")
    account_type: str | None = Field(
        default=None, max_length=50, description="Verified, Basic, etc"
    )
    region: str = Field(max_length=100, description="Geographic region")
    city: str | None = Field(default=None, max_length=100, description="City name")

    # Issue classification
    category: str = Field(max_length=100, description="Issue category")
    subcategory: str | None = Field(default=None, max_length=100, description="Issue subcategory")
    summary: str = Field(max_length=500, description="Brief issue description")
    description: str | None = Field(default=None, description="Detailed issue description")

    # Transaction metadata
    transaction_id: str | None = Field(
        default=None, max_length=100, description="Related transaction ID"
    )
    amount: float | None = Field(default=None, ge=0, description="Transaction amount")
    currency: str | None = Field(default=None, max_length=3, description="Currency code (PHP, USD)")
    merchant: str | None = Field(default=None, max_length=255, description="Bank/merchant name")
    occurred_at: datetime | None = Field(default=None, description="When the issue occurred")

    # Clustering and merge references
    merged_into_id: UUID | None = Field(default=None, description="If merged, primary ticket ID")
    cluster_id: UUID | None = Field(default=None, description="Associated cluster ID")

    # Raw metadata from source system
    raw_metadata: dict[str, Any] | None = Field(default=None, description="Original ticket data")

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        if self.merged_into_id:
            doc["mergedIntoId"] = str(self.merged_into_id)
        if self.cluster_id:
            doc["clusterId"] = str(self.cluster_id)
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> Ticket:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    @staticmethod
    def generate_partition_key(region: str, created_at: datetime) -> str:
        """Generate partition key from region and date."""
        year_month = created_at.strftime("%Y-%m")
        return f"{region}|{year_month}"
