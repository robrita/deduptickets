"""
MergeOperation domain model.

Represents a completed merge action with full ticket snapshots for revert capability.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class MergeBehavior(StrEnum):
    """Merge behavior options."""

    KEEP_LATEST = "keep_latest"
    COMBINE_NOTES = "combine_notes"
    RETAIN_ALL = "retain_all"


class MergeStatus(StrEnum):
    """Merge operation status."""

    PENDING = "pending"
    COMPLETED = "completed"
    REVERTED = "reverted"


class TicketSnapshot(BaseModel):
    """
    Complete ticket snapshot for revert capability.

    Stores the full ticket state before merge per FR-012.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    ticket_id: UUID
    snapshot: dict[str, Any] = Field(description="Full ticket document at merge time")


class MergeOperation(BaseModel):
    """
    MergeOperation entity tracking a completed merge.

    Aligned with data-model.md merges container schema.
    Stores original ticket states for 100% reversibility (FR-011, FR-012).
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Merge operation identifier")
    pk: str = Field(description="Partition key: {year-month}")

    # Merge references
    cluster_id: UUID = Field(description="Source cluster")
    primary_ticket_id: UUID = Field(description="Merge target ticket")
    secondary_ticket_ids: list[UUID] = Field(description="Tickets merged into primary")

    # Merge configuration
    merge_behavior: MergeBehavior = Field(
        default=MergeBehavior.KEEP_LATEST, description="How to combine ticket data"
    )

    # Status tracking
    status: MergeStatus = Field(default=MergeStatus.COMPLETED)

    # Actor and timestamps
    performed_by: str = Field(description="Actor identity")
    performed_at: datetime = Field(default_factory=datetime.utcnow)

    # Revert tracking
    revert_deadline: datetime | None = Field(default=None, description="Deadline for revert")
    reverted_at: datetime | None = Field(default=None)
    reverted_by: str | None = Field(default=None)
    revert_reason: str | None = Field(default=None)

    # Full ticket snapshots for revert (FR-012)
    original_states: list[TicketSnapshot] = Field(
        default_factory=list,
        description="Full ticket snapshots for revert capability",
    )

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format (camelCase)."""
        doc = self.model_dump(mode="json", by_alias=True)
        doc["id"] = str(self.id)
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> MergeOperation:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    def revert(self, actor_id: str, reason: str | None = None) -> None:
        """Mark the merge as reverted."""
        if self.status == MergeStatus.REVERTED:
            msg = "Merge is already reverted"
            raise ValueError(msg)
        self.status = MergeStatus.REVERTED
        self.reverted_by = actor_id
        self.reverted_at = datetime.utcnow()
        self.revert_reason = reason

    def get_snapshot(self, ticket_id: UUID) -> dict[str, Any] | None:
        """Get the original snapshot for a ticket."""
        for state in self.original_states:
            if state.ticket_id == ticket_id:
                return state.snapshot
        return None
