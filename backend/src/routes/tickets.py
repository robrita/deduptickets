"""
Ticket management endpoints.

Provides CRUD operations for support tickets with clustering integration.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import (
    ApiKeyDep,
    ClusteringServiceDep,
    CurrentUserDep,
    EmbeddingServiceDep,
    TicketRepoDep,
)
from lib.embedding import build_dedup_text
from models.ticket import Ticket, TicketPriority, TicketStatus
from schemas.common import PaginationMeta
from schemas.ticket import (
    TicketChannel as SchemaChannel,
)
from schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
)
from schemas.ticket import (
    TicketPriority as SchemaPriority,
)
from schemas.ticket import (
    TicketSeverity as SchemaSeverity,
)
from schemas.ticket import (
    TicketStatus as SchemaStatus,
)

# Mapping for channel values from database to schema enum
_CHANNEL_MAP = {
    "in_app": SchemaChannel.IN_APP,
    "inapp": SchemaChannel.IN_APP,
    "in-app": SchemaChannel.IN_APP,
    "chat": SchemaChannel.CHAT,
    "email": SchemaChannel.EMAIL,
    "social": SchemaChannel.SOCIAL,
    "phone": SchemaChannel.PHONE,
}

# Mapping for status values from database to schema enum
_STATUS_MAP = {
    "open": SchemaStatus.OPEN,
    "pending": SchemaStatus.PENDING,
    "resolved": SchemaStatus.RESOLVED,
    "closed": SchemaStatus.CLOSED,
    "merged": SchemaStatus.MERGED,
}


def _normalize_channel(channel: str | None) -> SchemaChannel:
    """Normalize channel value to schema enum."""
    if not channel:
        return SchemaChannel.IN_APP
    normalized = channel.lower().replace(" ", "_").replace("-", "_")
    return _CHANNEL_MAP.get(normalized, SchemaChannel.IN_APP)


def _normalize_status(status_value: str) -> SchemaStatus:
    """Normalize status value to schema enum."""
    return _STATUS_MAP.get(status_value.lower(), SchemaStatus.OPEN)


# Fields on the Ticket model that are internal-only (not exposed in API responses).
_TICKET_INTERNAL_FIELDS = {"pk", "content_vector", "dedup_text", "dedup", "raw_metadata"}


def _ticket_to_response(t: Ticket) -> TicketResponse:
    """Convert Ticket model to TicketResponse schema.

    Uses model_dump() so new fields added to both Ticket and TicketResponse
    flow through automatically without manual mapping.
    """
    data = t.model_dump(exclude=_TICKET_INTERNAL_FIELDS)

    # Normalize enums from model values → schema enum values
    data["status"] = _normalize_status(t.status.value)
    data["priority"] = SchemaPriority(t.priority.value) if t.priority else None
    data["severity"] = SchemaSeverity(t.severity) if t.severity else None
    data["channel"] = _normalize_channel(t.channel)

    # Derived field: extract decision from dedup metadata dict
    data["dedup_decision"] = (
        t.dedup.get("decision") if t.dedup and isinstance(t.dedup, dict) else None
    )

    return TicketResponse.model_validate(data)


router = APIRouter()


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new ticket",
    description="Submit a new support ticket for duplicate analysis and clustering.",
)
async def create_ticket(
    ticket_data: TicketCreate,
    ticket_repo: TicketRepoDep,
    clustering_service: ClusteringServiceDep,
    embedding_service: EmbeddingServiceDep,
    _api_key: ApiKeyDep,
    _current_user: CurrentUserDep,
) -> TicketResponse:
    """
    Ingest a new support ticket.

    Generates embedding, runs cluster-first dedup, then persists
    ticket in a single write with vector + cluster assignment.
    Returns 503 if embedding generation fails.
    """
    # Build partition key from timestamp
    created_at = ticket_data.created_at
    partition_key = ticket_repo.build_partition_key(created_at)

    # Check for existing ticket with same ticket_number
    existing = await ticket_repo.get_by_ticket_number(ticket_data.ticket_number, partition_key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket with ticket_number '{ticket_data.ticket_number}' already exists",
        )

    # Build Ticket from TicketCreate using model_dump() for automatic field propagation.
    # Only fields needing enum conversion or defaults are handled explicitly.
    create_fields = ticket_data.model_dump(
        exclude={"status", "priority", "severity", "channel", "raw_metadata", "customer_id"}
    )
    ticket = Ticket(
        **create_fields,
        customer_id=ticket_data.customer_id or "",
        status=TicketStatus(ticket_data.status.value) if ticket_data.status else TicketStatus.OPEN,
        priority=(
            TicketPriority(ticket_data.priority.value)
            if ticket_data.priority
            else TicketPriority.MEDIUM
        ),
        severity=ticket_data.severity.value if ticket_data.severity else None,
        channel=ticket_data.channel.value if ticket_data.channel else "in_app",
        raw_metadata=ticket_data.raw_metadata or {},
        updated_at=created_at,
        pk=partition_key,
    )

    # Step 1: Generate embedding (fail fast → 503)
    dedup_text = build_dedup_text(ticket)
    try:
        content_vector = await embedding_service.generate_embedding(dedup_text)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding generation failed",
        ) from exc

    ticket.dedup_text = dedup_text
    ticket.content_vector = content_vector

    # Step 2: Cluster-first dedup (finds or creates cluster)
    cluster, dedup_meta = await clustering_service.find_or_create_cluster(
        ticket,
        partition_key,
    )

    # Step 3: Attach dedup metadata and cluster reference to ticket
    ticket.cluster_id = cluster.id
    ticket.dedup = dedup_meta

    # Step 4: Single write — persist ticket with vector + cluster + dedup
    created = await ticket_repo.create(ticket, partition_key)

    return _ticket_to_response(created)


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get ticket by ID",
    description="Retrieve a specific ticket by its ID.",
    responses={
        404: {"description": "Ticket not found"},
    },
)
async def get_ticket(
    ticket_id: UUID,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    ticket_repo: TicketRepoDep,
    _api_key: ApiKeyDep,
) -> TicketResponse:
    """Get a ticket by its ID."""
    partition_key = month

    ticket = await ticket_repo.get_by_id(ticket_id, partition_key)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    return _ticket_to_response(ticket)


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List tickets",
    description="List tickets with pagination, filtering, and sorting.",
)
async def list_tickets(
    ticket_repo: TicketRepoDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unassigned_only: Annotated[bool, Query(description="Only unassigned tickets")] = False,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    sort_by: Annotated[
        str, Query(description="Field to sort by (createdAt, priority, status)")
    ] = "createdAt",
    sort_order: Annotated[str, Query(description="Sort order (asc, desc)")] = "desc",
) -> TicketListResponse:
    """List tickets with pagination, filtering, and sorting."""
    partition_key = month
    offset = (page - 1) * page_size

    # Build WHERE clauses
    where_clauses = []
    parameters: list[dict[str, str]] = []

    if unassigned_only:
        where_clauses.append("(c.clusterId = null OR NOT IS_DEFINED(c.clusterId))")

    if status:
        where_clauses.append("c.status = @status")
        parameters.append({"name": "@status", "value": status})

    # Build full query
    where_clause = " AND ".join(where_clauses) if where_clauses else None

    # Validate sort_by to prevent injection
    allowed_sort_fields = {"createdAt", "priority", "status", "ticketNumber"}
    if sort_by not in allowed_sort_fields:
        sort_by = "createdAt"
    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
    order_by = f"c.{sort_by} {sort_direction}"

    # Get total count for pagination
    total = await ticket_repo.count(
        query=where_clause,
        parameters=parameters if parameters else None,
        partition_key=partition_key,
    )

    # Query tickets with pagination
    if where_clause:
        query = f"SELECT * FROM c WHERE {where_clause} ORDER BY {order_by}"  # noqa: S608  # nosec B608
    else:
        query = f"SELECT * FROM c ORDER BY {order_by}"  # noqa: S608  # nosec B608

    tickets = await ticket_repo.query(
        query,
        parameters=parameters if parameters else None,
        partition_key=partition_key,
        max_item_count=page_size,
        offset=offset,
    )

    items = [_ticket_to_response(t) for t in tickets]

    return TicketListResponse(
        data=items,
        meta=PaginationMeta(
            total=total,
            offset=offset,
            limit=page_size,
            has_more=(offset + len(items)) < total,
        ),
    )
