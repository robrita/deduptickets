"""Pydantic request/response schemas for DedupTickets API."""

from schemas.cluster import (
    ClusterDetail,
    ClusterDismissRequest,
    ClusterListResponse,
    ClusterResponse,
)
from schemas.common import ErrorResponse, HealthResponse, PaginationMeta
from schemas.merge import (
    MergeListResponse,
    MergeRequest,
    MergeResponse,
    RevertConflictResponse,
    RevertRequest,
)
from schemas.ticket import TicketCreate, TicketListResponse, TicketResponse

__all__ = [
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
    # Ticket
    "TicketCreate",
    "TicketListResponse",
    "TicketResponse",
]
