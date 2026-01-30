"""Pydantic request/response schemas for DedupTickets API."""

from deduptickets.schemas.audit import AuditListResponse, AuditResponse, AuditSearchParams
from deduptickets.schemas.cluster import (
    ClusterDetail,
    ClusterDismissRequest,
    ClusterListResponse,
    ClusterResponse,
)
from deduptickets.schemas.common import ErrorResponse, HealthResponse, PaginationMeta
from deduptickets.schemas.merge import (
    MergeListResponse,
    MergeRequest,
    MergeResponse,
    RevertConflictResponse,
    RevertRequest,
)
from deduptickets.schemas.spike import (
    SpikeAcknowledgeRequest,
    SpikeDetail,
    SpikeListResponse,
    SpikeResolveRequest,
    SpikeResponse,
)
from deduptickets.schemas.ticket import TicketCreate, TicketListResponse, TicketResponse

__all__ = [
    "AuditListResponse",
    # Audit
    "AuditResponse",
    "AuditSearchParams",
    "ClusterDetail",
    "ClusterDismissRequest",
    "ClusterListResponse",
    # Cluster
    "ClusterResponse",
    "ErrorResponse",
    "HealthResponse",
    "MergeListResponse",
    # Merge
    "MergeRequest",
    "MergeResponse",
    # Common
    "PaginationMeta",
    "RevertConflictResponse",
    "RevertRequest",
    "SpikeAcknowledgeRequest",
    "SpikeDetail",
    "SpikeListResponse",
    "SpikeResolveRequest",
    # Spike
    "SpikeResponse",
    # Ticket
    "TicketCreate",
    "TicketListResponse",
    "TicketResponse",
]
