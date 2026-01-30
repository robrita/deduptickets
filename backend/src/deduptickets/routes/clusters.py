"""
Cluster management endpoints.

Provides operations for viewing and managing duplicate clusters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, HTTPException, Query, status

from deduptickets.models.audit_entry import AuditAction
from deduptickets.models.cluster import ClusterStatus
from deduptickets.schemas.cluster import (
    ClusterDetail,
    ClusterDismissRequest,
    ClusterListResponse,
    ClusterResponse,
)
from deduptickets.schemas.common import PaginationMeta
from deduptickets.schemas.ticket import TicketResponse

if TYPE_CHECKING:
    from uuid import UUID

    from deduptickets.dependencies import (
        ApiKeyDep,
        AuditRepoDep,
        ClusterRepoDep,
        CurrentUserDep,
        RequestContextDep,
        TicketRepoDep,
    )

router = APIRouter()


@router.get(
    "",
    response_model=ClusterListResponse,
    summary="List clusters",
    description="List duplicate clusters with filtering and pagination.",
)
async def list_clusters(
    cluster_repo: ClusterRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[ClusterStatus | None, Query(alias="status")] = None,
    min_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
) -> ClusterListResponse:
    """List clusters with filtering."""
    partition_key = f"{region}|{month}"

    if status_filter:
        clusters = await cluster_repo.get_by_status(status_filter, partition_key, limit=page_size)
    elif min_confidence:
        clusters = await cluster_repo.get_high_confidence_clusters(
            min_confidence, partition_key, limit=page_size
        )
    else:
        clusters = await cluster_repo.get_pending_clusters(partition_key, limit=page_size)

    items = [
        ClusterResponse(
            id=c.id,
            ticket_ids=c.ticket_ids,
            ticket_count=c.ticket_count,
            confidence_score=c.confidence_score,
            status=c.status.value,
            matching_fields=c.matching_fields,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in clusters
    ]

    return ClusterListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )


@router.get(
    "/{cluster_id}",
    response_model=ClusterDetail,
    summary="Get cluster details",
    description="Get detailed information about a cluster including all tickets.",
    responses={
        404: {"description": "Cluster not found"},
    },
)
async def get_cluster(
    cluster_id: UUID,
    cluster_repo: ClusterRepoDep,
    ticket_repo: TicketRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterDetail:
    """Get cluster with full ticket details."""
    partition_key = f"{region}|{month}"

    cluster = await cluster_repo.get_by_id(cluster_id, partition_key)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found",
        )

    # Fetch all tickets in the cluster
    tickets = await ticket_repo.get_by_cluster_id(cluster_id, partition_key)

    ticket_responses = [
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

    return ClusterDetail(
        id=cluster.id,
        ticket_ids=cluster.ticket_ids,
        ticket_count=cluster.ticket_count,
        confidence_score=cluster.confidence_score,
        status=cluster.status.value,
        matching_fields=cluster.matching_fields,
        created_at=cluster.created_at,
        updated_at=cluster.updated_at,
        tickets=ticket_responses,
        dismissed_by=cluster.dismissed_by,
        dismissal_reason=cluster.dismissal_reason,
    )


@router.post(
    "/{cluster_id}/dismiss",
    response_model=ClusterResponse,
    summary="Dismiss a cluster",
    description="Mark a cluster as dismissed (not a valid duplicate group).",
    responses={
        404: {"description": "Cluster not found"},
    },
)
async def dismiss_cluster(
    cluster_id: UUID,
    dismiss_request: ClusterDismissRequest,
    cluster_repo: ClusterRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterResponse:
    """Dismiss a cluster as not valid duplicates."""
    partition_key = f"{region}|{month}"

    cluster = await cluster_repo.get_by_id(cluster_id, partition_key)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found",
        )

    if cluster.status == ClusterStatus.DISMISSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cluster is already dismissed",
        )

    # Update cluster status
    updated = await cluster_repo.update_status(
        cluster_id,
        ClusterStatus.DISMISSED,
        partition_key,
        dismissed_by=current_user,
        dismissal_reason=dismiss_request.reason,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cluster",
        )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="cluster",
        entity_id=cluster_id,
        action=AuditAction.CLUSTER_DISMISSED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        changes={
            "status": {"before": cluster.status.value, "after": ClusterStatus.DISMISSED.value},
            "dismissal_reason": dismiss_request.reason,
        },
    )

    return ClusterResponse(
        id=updated.id,
        ticket_ids=updated.ticket_ids,
        ticket_count=updated.ticket_count,
        confidence_score=updated.confidence_score,
        status=updated.status.value,
        matching_fields=updated.matching_fields,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.get(
    "/pending/count",
    summary="Get pending cluster count",
    description="Get the count of clusters pending review.",
)
async def get_pending_count(
    cluster_repo: ClusterRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str | None, Query(description="Region filter")] = None,
    month: Annotated[str | None, Query(description="Month filter")] = None,
) -> dict[str, int]:
    """Get count of pending clusters."""
    partition_key = f"{region}|{month}" if region and month else None
    count = await cluster_repo.get_pending_review_count(partition_key)
    return {"pending_count": count}


@router.delete(
    "/{cluster_id}/members/{ticket_id}",
    response_model=ClusterResponse,
    summary="Remove ticket from cluster",
    description="Remove a specific ticket from a cluster.",
    responses={
        404: {"description": "Cluster or ticket not found"},
        400: {"description": "Invalid operation"},
    },
)
async def remove_cluster_member(
    cluster_id: UUID,
    ticket_id: UUID,
    cluster_repo: ClusterRepoDep,
    ticket_repo: TicketRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterResponse:
    """Remove a ticket from a cluster."""
    partition_key = f"{region}|{month}"

    # Validate cluster exists
    cluster = await cluster_repo.get_by_id(cluster_id, partition_key)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found",
        )

    # Validate ticket is in cluster
    if ticket_id not in cluster.ticket_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket {ticket_id} is not in cluster {cluster_id}",
        )

    # Cannot remove from non-pending cluster
    if cluster.status != ClusterStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify cluster with status {cluster.status.value}",
        )

    # Remove ticket from cluster
    updated_cluster = await cluster_repo.remove_ticket(cluster_id, ticket_id, partition_key)

    # Update ticket to remove cluster reference
    await ticket_repo.remove_from_cluster(ticket_id, partition_key)

    if not updated_cluster:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove ticket from cluster",
        )

    # Auto-dismiss if cluster is too small
    if updated_cluster.ticket_count < 2:
        updated_cluster = await cluster_repo.update_status(
            cluster_id,
            ClusterStatus.DISMISSED,
            partition_key,
            dismissal_reason="Cluster became too small after ticket removal",
        )
        if not updated_cluster:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update cluster status",
            )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="cluster",
        entity_id=cluster_id,
        action=AuditAction.CLUSTER_MODIFIED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        changes={
            "ticket_removed": str(ticket_id),
            "ticket_count": {"before": cluster.ticket_count, "after": updated_cluster.ticket_count},
        },
    )

    return ClusterResponse(
        id=updated_cluster.id,
        ticket_ids=updated_cluster.ticket_ids,
        ticket_count=updated_cluster.ticket_count,
        confidence_score=updated_cluster.confidence_score,
        status=updated_cluster.status.value,
        matching_fields=updated_cluster.matching_fields,
        created_at=updated_cluster.created_at,
        updated_at=updated_cluster.updated_at,
    )
