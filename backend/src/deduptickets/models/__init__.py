"""Pydantic domain models for DedupTickets."""

from deduptickets.models.audit_entry import (
    ActorType,
    AuditAction,
    AuditActionType,
    AuditEntry,
    AuditOutcome,
)
from deduptickets.models.baseline import Baseline
from deduptickets.models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
    ConfidenceLevel,
    ExactMatch,
    MatchingSignals,
    TextSimilarity,
    TimeWindow,
)
from deduptickets.models.merge_operation import (
    MergeBehavior,
    MergeOperation,
    MergeStatus,
    TicketSnapshot,
)
from deduptickets.models.spike_alert import SeverityLevel, SpikeAlert, SpikeStatus
from deduptickets.models.ticket import Ticket, TicketPriority, TicketStatus

__all__ = [
    "ActorType",
    "AuditAction",
    "AuditActionType",
    # Audit
    "AuditEntry",
    "AuditOutcome",
    # Baseline
    "Baseline",
    # Cluster
    "Cluster",
    "ClusterMember",
    "ClusterStatus",
    "ConfidenceLevel",
    "ExactMatch",
    "MatchingSignals",
    "MergeBehavior",
    # Merge
    "MergeOperation",
    "MergeStatus",
    "SeverityLevel",
    # Spike
    "SpikeAlert",
    "SpikeStatus",
    "TextSimilarity",
    # Ticket
    "Ticket",
    "TicketPriority",
    "TicketSnapshot",
    "TicketStatus",
    "TimeWindow",
]
