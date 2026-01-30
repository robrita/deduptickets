"""
AuditEntry domain model.

Immutable log record for significant system actions.
Constitution Principle II: Audit logging for all key actions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AuditAction(StrEnum):
    """Types of auditable actions."""

    # Merge operations
    MERGE_COMPLETED = "merge_completed"
    MERGE_REVERTED = "merge_reverted"

    # Cluster operations
    CLUSTER_CREATED = "cluster_created"
    CLUSTER_DISMISSED = "cluster_dismissed"
    CLUSTER_MODIFIED = "cluster_modified"

    # Spike operations
    SPIKE_ACKNOWLEDGED = "spike_acknowledged"
    SPIKE_RESOLVED = "spike_resolved"

    # Legacy aliases (deprecated)
    MERGE = "merge"
    REVERT = "revert"
    CLUSTER_CREATE = "cluster_create"
    CLUSTER_DISMISS = "cluster_dismiss"
    CLUSTER_MEMBER_REMOVE = "cluster_member_remove"
    SPIKE_ACKNOWLEDGE = "spike_acknowledge"
    SPIKE_RESOLVE = "spike_resolve"


# Alias for backward compatibility
AuditActionType = AuditAction


class ActorType(StrEnum):
    """Type of actor performing the action."""

    USER = "user"
    SYSTEM = "system"


class AuditOutcome(StrEnum):
    """Outcome of the action."""

    SUCCESS = "success"
    FAILURE = "failure"


class AuditEntry(BaseModel):
    """
    AuditEntry entity for immutable action logging.

    Aligned with data-model.md audit container schema.
    Supports FR-025, FR-026, FR-027, FR-028.
    """

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Audit entry identifier")
    pk: str = Field(description="Partition key: {year-month}")

    # Action details
    action_type: AuditActionType = Field(description="Type of action performed")
    actor_id: str = Field(description="Identity of the actor")
    actor_type: ActorType = Field(default=ActorType.USER)

    # Resource references
    resource_type: str = Field(description="Type of resource affected (Ticket, Cluster, etc)")
    resource_id: UUID = Field(description="Primary resource identifier")
    related_ids: list[UUID] = Field(default_factory=list, description="Related resource IDs")

    # Action metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (mergeBehavior, ticketCount, etc)",
    )

    # Outcome tracking
    outcome: AuditOutcome = Field(default=AuditOutcome.SUCCESS)
    error_message: str | None = Field(default=None, description="Error details if failed")

    # Request context
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)

    # Timestamps (ISO 8601 per Constitution)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # TTL for automatic cleanup (default 90 days = 7776000 seconds)
    ttl: int = Field(default=7776000, description="TTL in seconds, -1 for indefinite")

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        doc["resourceId"] = str(self.resource_id)
        doc["relatedIds"] = [str(rid) for rid in self.related_ids]
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> AuditEntry:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    @staticmethod
    def generate_partition_key(timestamp: datetime) -> str:
        """Generate partition key from timestamp."""
        return timestamp.strftime("%Y-%m")

    @classmethod
    def create_merge_entry(
        cls,
        actor_id: str,
        cluster_id: UUID,
        primary_ticket_id: UUID,
        secondary_ticket_ids: list[UUID],
        merge_behavior: str,
        *,
        ip_address: str | None = None,
    ) -> AuditEntry:
        """Factory method for merge action audit entry."""
        now = datetime.utcnow()
        return cls(
            pk=cls.generate_partition_key(now),
            action_type=AuditActionType.MERGE,
            actor_id=actor_id,
            resource_type="Cluster",
            resource_id=cluster_id,
            related_ids=[primary_ticket_id, *secondary_ticket_ids],
            metadata={
                "mergeBehavior": merge_behavior,
                "ticketCount": len(secondary_ticket_ids) + 1,
            },
            ip_address=ip_address,
            created_at=now,
        )

    @classmethod
    def create_revert_entry(
        cls,
        actor_id: str,
        merge_id: UUID,
        cluster_id: UUID,
        restored_ticket_ids: list[UUID],
        reason: str | None = None,
        *,
        ip_address: str | None = None,
    ) -> AuditEntry:
        """Factory method for revert action audit entry."""
        now = datetime.utcnow()
        return cls(
            pk=cls.generate_partition_key(now),
            action_type=AuditActionType.REVERT,
            actor_id=actor_id,
            resource_type="MergeOperation",
            resource_id=merge_id,
            related_ids=[cluster_id, *restored_ticket_ids],
            metadata={
                "reason": reason,
                "restoredCount": len(restored_ticket_ids),
            },
            ip_address=ip_address,
            created_at=now,
        )
