"""
Merge operation endpoints.

Provides operations for merging duplicate tickets and reverting merges.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import (
    ApiKeyDep,
    ClusterRepoDep,
    CurrentUserDep,
    MergeRepoDep,
    TicketRepoDep,
)
from models.cluster import ClusterStatus
from models.merge_operation import MergeBehavior, MergeOperation, MergeStatus
from schemas.common import PaginationMeta
from schemas.merge import (
    MergeBehavior as SchemaMergeBehavior,
)
from schemas.merge import (
    MergeListResponse,
    MergeRequest,
    MergeResponse,
    RevertConflict,
    RevertConflictResponse,
    RevertRequest,
)
from schemas.merge import (
    MergeStatus as SchemaMergeStatus,
)

router = APIRouter()

# Fields on the MergeOperation model that are internal-only (not exposed in API responses).
_MERGE_INTERNAL_FIELDS = {"pk", "original_states", "revert_deadline"}


def _merge_to_response(m: MergeOperation) -> MergeResponse:
    """Convert MergeOperation model to MergeResponse schema.

    Uses model_dump() so new fields added to both MergeOperation and MergeResponse
    flow through automatically without manual mapping.
    """
    data = m.model_dump(exclude=_MERGE_INTERNAL_FIELDS)

    # Normalize enums from model StrEnum → schema str Enum
    data["merge_behavior"] = SchemaMergeBehavior(m.merge_behavior.value)
    data["status"] = SchemaMergeStatus(m.status.value)

    return MergeResponse.model_validate(data)


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
    current_user: CurrentUserDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """
    Merge duplicate tickets.

    Creates a merge operation that designates one ticket as canonical
    and marks others as duplicates.
    """
    partition_key = month

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
    canonical_ticket = await ticket_repo.get_by_id(merge_request.primary_ticket_id, partition_key)
    if not canonical_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Primary ticket {merge_request.primary_ticket_id} not found",
        )

    if merge_request.primary_ticket_id not in cluster.ticket_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary ticket is not in the cluster",
        )

    # Get merged ticket IDs (all tickets in cluster except canonical)
    merged_ticket_ids = [
        tid for tid in cluster.ticket_ids if tid != merge_request.primary_ticket_id
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
        primary_ticket_id=merge_request.primary_ticket_id,
        secondary_ticket_ids=merged_ticket_ids,
        merge_behavior=MergeBehavior(merge_request.merge_behavior.value)
        if merge_request.merge_behavior
        else MergeBehavior.KEEP_LATEST,
        performed_by=current_user,
        performed_at=now,
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

    return _merge_to_response(created)


@router.get(
    "",
    response_model=MergeListResponse,
    summary="List merge operations",
    description="List merge operations with pagination.",
)
async def list_merges(
    merge_repo: MergeRepoDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    revertible_only: Annotated[bool, Query(description="Only revertible merges")] = False,
) -> MergeListResponse:
    """List merge operations."""
    partition_key = month

    if revertible_only:
        merges = await merge_repo.get_revertible_merges(partition_key, limit=page_size)
    else:
        query = "SELECT * FROM c ORDER BY c.performedAt DESC"
        merges = await merge_repo.query(
            query, partition_key=partition_key, max_item_count=page_size
        )

    items = [_merge_to_response(m) for m in merges]

    return MergeListResponse(
        data=items,
        meta=PaginationMeta(
            total=len(items),
            offset=(page - 1) * page_size,
            limit=page_size,
            has_more=False,
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
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """Get a merge operation by ID."""
    partition_key = month

    merge = await merge_repo.get_by_id(merge_id, partition_key)
    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge {merge_id} not found",
        )

    return _merge_to_response(merge)


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
    current_user: CurrentUserDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> MergeResponse:
    """
    Revert a merge operation.

    Only allowed within the revert window (24 hours by default).
    Checks for conflicts with subsequent merges.
    """
    partition_key = month

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

    return _merge_to_response(updated)


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
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> RevertConflictResponse:
    """Check for conflicts before reverting."""
    partition_key = month

    merge = await merge_repo.get_by_id(merge_id, partition_key)
    if not merge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merge {merge_id} not found",
        )

    conflicts = await merge_repo.check_revert_conflicts(merge_id, partition_key)

    if conflicts:
        return RevertConflictResponse(
            error="CONFLICT",
            message=f"Cannot revert merge {merge_id}: conflicts with subsequent merges",
            conflicts=[
                RevertConflict(
                    ticket_id=c.primary_ticket_id,
                    field="merge_status",
                    original_value=None,
                    current_value=c.status.value,
                )
                for c in conflicts
            ],
        )

    return RevertConflictResponse(
        error="OK",
        message="No conflicts detected",
        conflicts=[],
    )
