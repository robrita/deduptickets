"""
Cluster management endpoints.

Provides operations for viewing and managing duplicate clusters.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from dependencies import (
    ApiKeyDep,
    ClusteringServiceDep,
    ClusterRepoDep,
    CurrentUserDep,
)
from models.cluster import Cluster, ClusterStatus
from schemas.cluster import (
    ClusterDetail,
    ClusterDismissRequest,
    ClusterListResponse,
    ClusterMemberResponse,
    ClusterResponse,
)
from schemas.cluster import (
    ClusterStatus as SchemaClusterStatus,
)
from schemas.common import PaginationMeta

router = APIRouter()

# Fields on the Cluster model that are internal-only (not exposed in API responses).
_CLUSTER_INTERNAL_FIELDS = {"pk", "centroid_vector", "members", "etag"}


def _cluster_to_response(c: Cluster) -> ClusterResponse:
    """Convert a Cluster model to a ClusterResponse schema.

    Uses model_dump() so new fields added to both Cluster and ClusterResponse
    flow through automatically without manual mapping.
    """
    data = c.model_dump(exclude=_CLUSTER_INTERNAL_FIELDS)

    # Normalize enum from model StrEnum → schema str Enum
    data["status"] = SchemaClusterStatus(c.status.value)

    return ClusterResponse.model_validate(data)


@router.get(
    "",
    response_model=ClusterListResponse,
    summary="List clusters",
    description="List duplicate clusters with filtering and pagination.",
)
async def list_clusters(
    cluster_repo: ClusterRepoDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[ClusterStatus | None, Query(alias="status")] = None,
) -> ClusterListResponse:
    """List clusters with filtering."""
    partition_key = month

    if status_filter:
        clusters = await cluster_repo.get_by_status(status_filter, partition_key, limit=page_size)
    else:
        clusters = await cluster_repo.get_pending_clusters(partition_key, limit=page_size)

    items = [_cluster_to_response(c) for c in clusters]

    return ClusterListResponse(
        data=items,
        meta=PaginationMeta(
            total=len(items),
            offset=(page - 1) * page_size,
            limit=page_size,
            has_more=False,
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
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterDetail:
    """Get cluster with embedded member details."""
    partition_key = month

    cluster = await cluster_repo.get_by_id(cluster_id, partition_key)
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id} not found",
        )

    member_responses = [
        ClusterMemberResponse.model_validate(m.model_dump()) for m in cluster.members
    ]

    resp = _cluster_to_response(cluster)
    return ClusterDetail(
        **resp.model_dump(),
        members=member_responses,
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
    clustering_service: ClusteringServiceDep,
    current_user: CurrentUserDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterResponse:
    """Dismiss a cluster as not valid duplicates."""
    try:
        updated = await clustering_service.dismiss_cluster(
            cluster_id,
            month,
            dismissed_by=current_user,
            reason=dismiss_request.reason,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from None

    return _cluster_to_response(updated)


@router.get(
    "/pending/count",
    summary="Get pending cluster count",
    description="Get the count of clusters pending review.",
)
async def get_pending_count(
    cluster_repo: ClusterRepoDep,
    _api_key: ApiKeyDep,
    month: Annotated[str | None, Query(description="Month filter")] = None,
) -> dict[str, int]:
    """Get count of pending clusters."""
    partition_key = month
    count = await cluster_repo.get_pending_review_count(partition_key)
    return {"pendingCount": count}


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
    clustering_service: ClusteringServiceDep,
    _current_user: CurrentUserDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> ClusterResponse:
    """Remove a ticket from a cluster."""
    try:
        updated_cluster = await clustering_service.remove_ticket_from_cluster(
            cluster_id,
            ticket_id,
            month,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from None
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from None

    return _cluster_to_response(updated_cluster)
