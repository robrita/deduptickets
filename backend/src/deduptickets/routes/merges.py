"""
Merge operation endpoints.

Provides operations for merging duplicate tickets and reverting merges.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, HTTPException, Query, status

from deduptickets.models.audit_entry import AuditAction
from deduptickets.models.cluster import ClusterStatus
from deduptickets.models.merge_operation import MergeOperation, MergeStatus
from deduptickets.schemas.common import PaginationMeta
from deduptickets.schemas.merge import (
    MergeListResponse,
    MergeRequest,
    MergeResponse,
    RevertConflictResponse,
    RevertRequest,
)

if TYPE_CHECKING:
    from uuid import UUID

    from deduptickets.dependencies import (
        ApiKeyDep,
        AuditRepoDep,
        ClusterRepoDep,
        CurrentUserDep,
        MergeRepoDep,
        RequestContextDep,
        TicketRepoDep,
    )

router = APIRouter()


@router.post(
    "",
    response_model=MergeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Merge tickets",
    description="Merge duplicate tickets from a cluster into a canonical ticket.",
    responses={
        404: {"description": "Cluster or ticket not found"},
        400: {"description": "Invalid merge request"},
    },
)
async def create_merge(
    merge_request: MergeRequest,
    merge_repo: MergeRepoDep,
    cluster_repo: ClusterRepoDep,
    ticket_repo: TicketRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """
    Merge duplicate tickets.

    Creates a merge operation that designates one ticket as canonical
    and marks others as duplicates.
    """
    partition_key = f"{region}|{month}"

    # Validate cluster exists and is pending
    cluster = await cluster_repo.get_by_id(merge_request.cluster_id, partition_key)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {merge_request.cluster_id} not found",
        )

    if cluster.status != ClusterStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cluster status is {cluster.status.value}, expected 'pending'",
        )

    # Validate canonical ticket exists and is in cluster
    canonical_ticket = await ticket_repo.get_by_id(merge_request.canonical_ticket_id, partition_key)
    if not canonical_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical ticket {merge_request.canonical_ticket_id} not found",
        )

    if merge_request.canonical_ticket_id not in cluster.ticket_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Canonical ticket is not in the cluster",
        )

    # Get merged ticket IDs (all tickets in cluster except canonical)
    merged_ticket_ids = [
        tid for tid in cluster.ticket_ids if tid != merge_request.canonical_ticket_id
    ]

    if not merged_ticket_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tickets to merge",
        )

    # Create merge operation
    now = datetime.utcnow()
    merge = MergeOperation(
        cluster_id=merge_request.cluster_id,
        canonical_ticket_id=merge_request.canonical_ticket_id,
        merged_ticket_ids=merged_ticket_ids,
        merged_by=current_user,
        merged_at=now,
        status=MergeStatus.COMPLETED,
        revert_deadline=now + timedelta(hours=24),  # 24-hour revert window
        pk=partition_key,
    )

    created = await merge_repo.create(merge, partition_key)

    # Update cluster status to merged
    await cluster_repo.update_status(
        merge_request.cluster_id,
        ClusterStatus.MERGED,
        partition_key,
    )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="merge",
        entity_id=created.id,
        action=AuditAction.MERGE_COMPLETED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        metadata={
            "cluster_id": str(merge_request.cluster_id),
            "canonical_ticket_id": str(merge_request.canonical_ticket_id),
            "merged_count": len(merged_ticket_ids),
        },
    )

    return MergeResponse(
        id=created.id,
        cluster_id=created.cluster_id,
        canonical_ticket_id=created.canonical_ticket_id,
        merged_ticket_ids=created.merged_ticket_ids,
        status=created.status.value,
        merged_by=created.merged_by,
        merged_at=created.merged_at,
        revert_deadline=created.revert_deadline,
    )


@router.get(
    "",
    response_model=MergeListResponse,
    summary="List merge operations",
    description="List merge operations with pagination.",
)
async def list_merges(
    merge_repo: MergeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    revertible_only: Annotated[bool, Query(description="Only revertible merges")] = False,
) -> MergeListResponse:
    """List merge operations."""
    partition_key = f"{region}|{month}"

    if revertible_only:
        merges = await merge_repo.get_revertible_merges(partition_key, limit=page_size)
    else:
        query = "SELECT * FROM c ORDER BY c.merged_at DESC"
        merges = await merge_repo.query(
            query, partition_key=partition_key, max_item_count=page_size
        )

    items = [
        MergeResponse(
            id=m.id,
            cluster_id=m.cluster_id,
            canonical_ticket_id=m.canonical_ticket_id,
            merged_ticket_ids=m.merged_ticket_ids,
            status=m.status.value,
            merged_by=m.merged_by,
            merged_at=m.merged_at,
            revert_deadline=m.revert_deadline,
            reverted_by=m.reverted_by,
            reverted_at=m.reverted_at,
        )
        for m in merges
    ]

    return MergeListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )


@router.get(
    "/{merge_id}",
    response_model=MergeResponse,
    summary="Get merge operation",
    description="Get details of a specific merge operation.",
    responses={
        404: {"description": "Merge not found"},
    },
)
async def get_merge(
    merge_id: UUID,
    merge_repo: MergeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """Get a merge operation by ID."""
    partition_key = f"{region}|{month}"

    merge = await merge_repo.get_by_id(merge_id, partition_key)
    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge {merge_id} not found",
        )

    return MergeResponse(
        id=merge.id,
        cluster_id=merge.cluster_id,
        canonical_ticket_id=merge.canonical_ticket_id,
        merged_ticket_ids=merge.merged_ticket_ids,
        status=merge.status.value,
        merged_by=merge.merged_by,
        merged_at=merge.merged_at,
        revert_deadline=merge.revert_deadline,
        reverted_by=merge.reverted_by,
        reverted_at=merge.reverted_at,
    )


@router.post(
    "/{merge_id}/revert",
    response_model=MergeResponse,
    summary="Revert a merge",
    description="Revert a merge operation within the revert window.",
    responses={
        404: {"description": "Merge not found"},
        400: {"description": "Revert not allowed"},
        409: {"description": "Conflicts with subsequent merges"},
    },
)
async def revert_merge(
    merge_id: UUID,
    revert_request: RevertRequest,
    merge_repo: MergeRepoDep,
    cluster_repo: ClusterRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """
    Revert a merge operation.

    Only allowed within the revert window (24 hours by default).
    Checks for conflicts with subsequent merges.
    """
    partition_key = f"{region}|{month}"

    merge = await merge_repo.get_by_id(merge_id, partition_key)
    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge {merge_id} not found",
        )

    if merge.status == MergeStatus.REVERTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Merge is already reverted",
        )

    # Check revert deadline
    now = datetime.utcnow()
    if merge.revert_deadline and now > merge.revert_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Revert window has expired",
        )

    # Check for conflicts
    conflicts = await merge_repo.check_revert_conflicts(merge_id, partition_key)
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revert: conflicts with subsequent merges",
        )

    # Update merge status
    updated = await merge_repo.update_status(
        merge_id,
        MergeStatus.REVERTED,
        partition_key,
        reverted_by=current_user,
        reverted_at=now,
        revert_reason=revert_request.reason,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revert merge",
        )

    # Revert cluster status back to pending
    await cluster_repo.update_status(
        merge.cluster_id,
        ClusterStatus.PENDING,
        partition_key,
    )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="merge",
        entity_id=merge_id,
        action=AuditAction.MERGE_REVERTED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        changes={
            "status": {"before": MergeStatus.COMPLETED.value, "after": MergeStatus.REVERTED.value},
            "reason": revert_request.reason,
        },
    )

    return MergeResponse(
        id=updated.id,
        cluster_id=updated.cluster_id,
        canonical_ticket_id=updated.canonical_ticket_id,
        merged_ticket_ids=updated.merged_ticket_ids,
        status=updated.status.value,
        merged_by=updated.merged_by,
        merged_at=updated.merged_at,
        revert_deadline=updated.revert_deadline,
        reverted_by=updated.reverted_by,
        reverted_at=updated.reverted_at,
    )


@router.get(
    "/{merge_id}/conflicts",
    response_model=RevertConflictResponse,
    summary="Check revert conflicts",
    description="Check if reverting a merge would cause conflicts.",
    responses={
        404: {"description": "Merge not found"},
    },
)
async def check_conflicts(
    merge_id: UUID,
    merge_repo: MergeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> RevertConflictResponse:
    """Check for conflicts before reverting."""
    partition_key = f"{region}|{month}"

    merge = await merge_repo.get_by_id(merge_id, partition_key)
    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge {merge_id} not found",
        )

    conflicts = await merge_repo.check_revert_conflicts(merge_id, partition_key)

    return RevertConflictResponse(
        merge_id=merge_id,
        has_conflicts=len(conflicts) > 0,
        conflicting_merge_ids=[c.id for c in conflicts],
        message="Conflicts found" if conflicts else "No conflicts",
    )
