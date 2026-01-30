"""
Cluster domain model.

Represents a proposed grouping of related/duplicate tickets.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClusterStatus(StrEnum):
    """Cluster status enumeration."""

    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ConfidenceLevel(StrEnum):
    """Confidence level for cluster matching."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExactMatch(BaseModel):
    """Exact field match signal."""

    field: str
    value: str


class TimeWindow(BaseModel):
    """Time window match signal."""

    start: datetime
    end: datetime


class TextSimilarity(BaseModel):
    """Text similarity match signal."""

    score: float = Field(ge=0.0, le=1.0)
    common_terms: list[str] = Field(default_factory=list)


class MatchingSignals(BaseModel):
    """
    Matching signals explaining why tickets were grouped.

    Provides explainability per FR-020 (no black box).
    """

    exact_matches: list[ExactMatch] = Field(default_factory=list)
    time_window: TimeWindow | None = None
    text_similarity: TextSimilarity | None = None
    field_matches: list[ExactMatch] = Field(default_factory=list)


class ClusterMember(BaseModel):
    """Reference to a ticket in the cluster."""

    ticket_id: UUID
    ticket_number: str
    is_primary: bool = False
    added_at: datetime = Field(default_factory=datetime.utcnow)


class Cluster(BaseModel):
    """
    Cluster entity representing a proposed grouping of related tickets.

    Aligned with data-model.md clusters container schema.
    """

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Cluster identifier")
    pk: str = Field(description="Partition key: {region}|{year-month}")

    # Cluster state
    status: ClusterStatus = Field(default=ClusterStatus.PENDING, description="Cluster status")
    confidence: ConfidenceLevel = Field(description="Matching confidence level")
    summary: str = Field(max_length=1000, description="Human-readable cluster summary")
    ticket_count: int = Field(ge=2, description="Number of tickets in cluster")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(default=None, description="Auto-expire if not actioned")

    # Ownership
    created_by: str = Field(default="system", description="system or user ID")

    # Matching explanation (FR-020: explainability)
    matching_signals: MatchingSignals = Field(default_factory=MatchingSignals)

    # Member tickets
    members: list[ClusterMember] = Field(default_factory=list, max_length=100)

    # Primary ticket (set after merge)
    primary_ticket_id: UUID | None = Field(default=None, description="Selected primary after merge")

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        if self.primary_ticket_id:
            doc["primaryTicketId"] = str(self.primary_ticket_id)
        # Convert member ticket IDs to strings
        for member in doc.get("members", []):
            member["ticketId"] = str(member.get("ticket_id", member.get("ticketId")))
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> Cluster:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    def add_member(self, ticket_id: UUID, ticket_number: str) -> None:
        """Add a ticket to the cluster."""
        if len(self.members) >= 100:
            msg = "Cluster member limit (100) reached"
            raise ValueError(msg)
        self.members.append(
            ClusterMember(
                ticket_id=ticket_id,
                ticket_number=ticket_number,
            )
        )
        self.ticket_count = len(self.members)
        self.updated_at = datetime.utcnow()

    def remove_member(self, ticket_id: UUID) -> bool:
        """Remove a ticket from the cluster. Returns True if removed."""
        original_count = len(self.members)
        self.members = [m for m in self.members if m.ticket_id != ticket_id]
        if len(self.members) < original_count:
            self.ticket_count = len(self.members)
            self.updated_at = datetime.utcnow()
            return True
        return False

    def set_primary(self, ticket_id: UUID) -> None:
        """Set a ticket as the primary for merge."""
        for member in self.members:
            member.is_primary = member.ticket_id == ticket_id
        self.primary_ticket_id = ticket_id
        self.updated_at = datetime.utcnow()

    @property
    def ticket_ids(self) -> list[UUID]:
        """Get list of ticket IDs in the cluster (convenience property)."""
        return [m.ticket_id for m in self.members]
