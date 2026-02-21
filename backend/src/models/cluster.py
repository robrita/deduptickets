"""
Cluster domain model.

Represents a proposed grouping of related/duplicate tickets.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ClusterStatus(StrEnum):
    """Cluster status enumeration."""

    CANDIDATE = "candidate"
    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ClusterMember(BaseModel):
    """Reference to a ticket in the cluster."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ticket_id: UUID
    ticket_number: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    summary: str | None = Field(default=None, max_length=500)
    category: str | None = None
    subcategory: str | None = None
    created_at: datetime | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class Cluster(BaseModel):
    """
    Cluster entity representing a proposed grouping of related tickets.

    Aligned with data-model.md clusters container schema.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Cluster identifier")
    pk: str = Field(description="Partition key: {year-month}")

    # Cluster state
    status: ClusterStatus = Field(default=ClusterStatus.PENDING, description="Cluster status")
    summary: str = Field(max_length=1000, description="Human-readable cluster summary")
    ticket_count: int = Field(ge=1, description="Number of tickets in cluster")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = Field(default=None, description="Auto-expire if not actioned")

    # Ownership
    created_by: str = Field(default="system", description="system or user ID")

    # Member tickets
    members: list[ClusterMember] = Field(default_factory=list, max_length=2000)

    # Vector / dedup fields
    centroid_vector: list[float] | None = Field(default=None, description="Cluster centroid vector")
    customer_id: str | None = Field(default=None, description="Customer scoping for dedup")
    category: str | None = Field(
        default=None, max_length=100, description="Category from representative ticket"
    )
    subcategory: str | None = Field(
        default=None, max_length=100, description="Subcategory from representative ticket"
    )
    open_count: int = Field(default=0, description="Number of open tickets in cluster")
    representative_ticket_id: UUID | None = Field(
        default=None, description="Most representative ticket"
    )

    # ETag for optimistic concurrency
    etag: str | None = Field(default=None, alias="_etag")

    # Dismissal tracking
    dismissed_by: str | None = Field(default=None, description="Who dismissed the cluster")
    dismissal_reason: str | None = Field(default=None, description="Why the cluster was dismissed")

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format (camelCase)."""
        doc = self.model_dump(mode="json", by_alias=True)
        doc["id"] = str(self.id)
        # _etag is server-managed; never send it back
        doc.pop("_etag", None)
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> Cluster:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    def add_member(
        self,
        ticket_id: UUID,
        ticket_number: str,
        *,
        summary: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        created_at: datetime | None = None,
        confidence_score: float | None = None,
        max_members: int = 100,
    ) -> None:
        """Add a ticket to the cluster."""
        if len(self.members) >= max_members:
            msg = f"Cluster member limit ({max_members}) reached"
            raise ValueError(msg)
        self.members.append(
            ClusterMember(
                ticket_id=ticket_id,
                ticket_number=ticket_number,
                summary=summary,
                category=category,
                subcategory=subcategory,
                created_at=created_at,
                confidence_score=confidence_score,
            )
        )
        self.ticket_count = len(self.members)
        self.updated_at = datetime.now(UTC)

    def remove_member(self, ticket_id: UUID) -> bool:
        """Remove a ticket from the cluster. Returns True if removed."""
        original_count = len(self.members)
        self.members = [m for m in self.members if m.ticket_id != ticket_id]
        if len(self.members) < original_count:
            self.ticket_count = len(self.members)
            self.updated_at = datetime.now(UTC)
            return True
        return False

    @property
    def ticket_ids(self) -> list[UUID]:
        """Get list of ticket IDs in the cluster (convenience property)."""
        return [m.ticket_id for m in self.members]
