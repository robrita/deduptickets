"""
Ticket management endpoints.

Provides CRUD operations for support tickets with clustering integration.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from deduptickets.models.ticket import Ticket
from deduptickets.schemas.common import PaginationMeta
from deduptickets.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
)
from deduptickets.services.clustering_service import ClusteringService

if TYPE_CHECKING:
    from uuid import UUID

    from deduptickets.dependencies import (
        ApiKeyDep,
        ClusterRepoDep,
        CurrentUserDep,
        TicketRepoDep,
    )

router = APIRouter()


def get_clustering_service(
    ticket_repo: TicketRepoDep,
    cluster_repo: ClusterRepoDep,
) -> ClusteringService:
    """Get clustering service with injected repositories."""
    return ClusteringService(ticket_repo, cluster_repo)


ClusteringServiceDep = Annotated[ClusteringService, Depends(get_clustering_service)]


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
    _api_key: ApiKeyDep,
    _current_user: CurrentUserDep,
) -> TicketResponse:
    """
    Ingest a new support ticket.

    The ticket will be analyzed for duplicates and potentially
    assigned to a cluster. Clustering runs synchronously (<30s).
    """
    # Build partition key from region and timestamp
    created_at = datetime.utcnow()
    partition_key = ticket_repo.build_partition_key(ticket_data.region, created_at)

    # Check for existing ticket with same source_id
    existing = await ticket_repo.get_by_source_id(ticket_data.source_id, partition_key)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ticket with source_id '{ticket_data.source_id}' already exists",
        )

    # Create ticket model
    ticket = Ticket(
        source_id=ticket_data.source_id,
        source_system=ticket_data.source_system,
        title=ticket_data.title,
        description=ticket_data.description,
        severity=ticket_data.severity,
        product=ticket_data.product,
        region=ticket_data.region,
        created_at=created_at,
        raw_metadata=ticket_data.metadata or {},
        pk=partition_key,
    )

    created = await ticket_repo.create(ticket, partition_key)

    # Trigger clustering analysis (synchronous, <30s per constitution)
    cluster = await clustering_service.find_or_create_cluster(created, partition_key)

    # Refresh ticket to get updated cluster_id if assigned
    if cluster:
        created = await ticket_repo.get_by_id(created.id, partition_key) or created

    return TicketResponse(
        id=created.id,
        source_id=created.source_id,
        source_system=created.source_system,
        title=created.title,
        description=created.description,
        severity=created.severity,
        product=created.product,
        region=created.region,
        cluster_id=created.cluster_id,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


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
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    ticket_repo: TicketRepoDep,
    _api_key: ApiKeyDep,
) -> TicketResponse:
    """Get a ticket by its ID."""
    partition_key = f"{region}|{month}"

    ticket = await ticket_repo.get_by_id(ticket_id, partition_key)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    return TicketResponse(
        id=ticket.id,
        source_id=ticket.source_id,
        source_system=ticket.source_system,
        title=ticket.title,
        description=ticket.description,
        severity=ticket.severity,
        product=ticket.product,
        region=ticket.region,
        cluster_id=ticket.cluster_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


@router.get(
    "",
    response_model=TicketListResponse,
    summary="List tickets",
    description="List tickets with pagination and filtering.",
)
async def list_tickets(
    ticket_repo: TicketRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unassigned_only: Annotated[bool, Query(description="Only unassigned tickets")] = False,
) -> TicketListResponse:
    """List tickets with pagination."""
    partition_key = f"{region}|{month}"

    if unassigned_only:
        tickets = await ticket_repo.get_unassigned_tickets(partition_key, limit=page_size)
    else:
        # General query for all tickets
        query = "SELECT * FROM c ORDER BY c.created_at DESC"
        tickets = await ticket_repo.query(
            query, partition_key=partition_key, max_item_count=page_size
        )

    items = [
        TicketResponse(
            id=t.id,
            source_id=t.source_id,
            source_system=t.source_system,
            title=t.title,
            description=t.description,
            severity=t.severity,
            product=t.product,
            region=t.region,
            cluster_id=t.cluster_id,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tickets
    ]

    return TicketListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),  # TODO: Implement proper count
            total_pages=1,  # TODO: Implement proper pagination
        ),
    )
