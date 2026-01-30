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


class MergeBehavior(StrEnum):
    """Merge behavior options."""

    KEEP_LATEST = "keep_latest"
    COMBINE_NOTES = "combine_notes"
    RETAIN_ALL = "retain_all"


class MergeStatus(StrEnum):
    """Merge operation status."""

    COMPLETED = "completed"
    REVERTED = "reverted"


class TicketSnapshot(BaseModel):
    """
    Complete ticket snapshot for revert capability.

    Stores the full ticket state before merge per FR-012.
    """

    ticket_id: UUID
    snapshot: dict[str, Any] = Field(description="Full ticket document at merge time")


class MergeOperation(BaseModel):
    """
    MergeOperation entity tracking a completed merge.

    Aligned with data-model.md merges container schema.
    Stores original ticket states for 100% reversibility (FR-011, FR-012).
    """

    model_config = ConfigDict(populate_by_name=True)

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Merge operation identifier")
    pk: str = Field(description="Partition key: {region}|{year-month}")

    # Merge references
    cluster_id: UUID = Field(description="Source cluster")
    primary_ticket_id: UUID = Field(
        description="Merge target ticket", validation_alias="canonical_ticket_id"
    )
    secondary_ticket_ids: list[UUID] = Field(
        description="Tickets merged into primary", validation_alias="merged_ticket_ids"
    )

    # Merge configuration
    merge_behavior: MergeBehavior = Field(
        default=MergeBehavior.KEEP_LATEST, description="How to combine ticket data"
    )

    # Status tracking
    status: MergeStatus = Field(default=MergeStatus.COMPLETED)

    # Actor and timestamps (Constitution Principle II: Audit logging)
    performed_by: str = Field(
        description="Actor identity", validation_alias="merged_by", serialization_alias="merged_by"
    )
    performed_at: datetime = Field(
        default_factory=datetime.utcnow,
        validation_alias="merged_at",
        serialization_alias="merged_at",
    )

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
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        doc["clusterId"] = str(self.cluster_id)
        doc["primaryTicketId"] = str(self.primary_ticket_id)
        doc["secondaryTicketIds"] = [str(tid) for tid in self.secondary_ticket_ids]
        # Convert snapshot ticket IDs
        for state in doc.get("originalStates", doc.get("original_states", [])):
            if "ticket_id" in state:
                state["ticketId"] = str(state.pop("ticket_id"))
            elif "ticketId" in state:
                state["ticketId"] = str(state["ticketId"])
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

    # Backward compatibility aliases
    @property
    def canonical_ticket_id(self) -> UUID:
        """Alias for primary_ticket_id (backward compatibility)."""
        return self.primary_ticket_id

    @property
    def merged_ticket_ids(self) -> list[UUID]:
        """Alias for secondary_ticket_ids (backward compatibility)."""
        return self.secondary_ticket_ids

    @property
    def merged_by(self) -> str:
        """Alias for performed_by (backward compatibility)."""
        return self.performed_by

    @property
    def merged_at(self) -> datetime:
        """Alias for performed_at (backward compatibility)."""
        return self.performed_at
