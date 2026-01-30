"""
Spike alert endpoints.

Provides operations for viewing and managing ticket volume spikes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, HTTPException, Query, status

from deduptickets.models.audit_entry import AuditAction
from deduptickets.models.spike_alert import SpikeStatus
from deduptickets.schemas.common import PaginationMeta
from deduptickets.schemas.spike import (
    SpikeAcknowledgeRequest,
    SpikeDetail,
    SpikeListResponse,
    SpikeResolveRequest,
    SpikeResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from deduptickets.dependencies import (
        ApiKeyDep,
        AuditRepoDep,
        CurrentUserDep,
        RequestContextDep,
        SpikeRepoDep,
    )

router = APIRouter()


@router.get(
    "",
    response_model=SpikeListResponse,
    summary="List spike alerts",
    description="List ticket volume spike alerts with filtering.",
)
async def list_spikes(
    spike_repo: SpikeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str | None, Query(description="Region filter")] = None,
    month: Annotated[str | None, Query(description="Month filter")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: Annotated[bool, Query(description="Only active spikes")] = True,
    product: Annotated[str | None, Query(description="Product filter")] = None,
) -> SpikeListResponse:
    """List spike alerts with filtering."""
    partition_key = f"{region}|{month}" if region and month else None

    if product:
        spikes = await spike_repo.get_by_product(product, partition_key, limit=page_size)
    elif active_only:
        spikes = await spike_repo.get_active_spikes(partition_key, limit=page_size)
    else:
        spikes = await spike_repo.get_recent_spikes(partition_key, hours=168, limit=page_size)

    items = [
        SpikeResponse(
            id=s.id,
            product=s.product,
            region=s.region,
            detected_at=s.detected_at,
            expected_count=s.expected_count,
            actual_count=s.actual_count,
            deviation_percent=s.deviation_percent,
            severity=s.severity,
            status=s.status.value,
        )
        for s in spikes
    ]

    return SpikeListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )


@router.get(
    "/{spike_id}",
    response_model=SpikeDetail,
    summary="Get spike details",
    description="Get detailed information about a spike alert.",
    responses={
        404: {"description": "Spike not found"},
    },
)
async def get_spike(
    spike_id: UUID,
    spike_repo: SpikeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> SpikeDetail:
    """Get spike alert details."""
    partition_key = f"{region}|{month}"

    spike = await spike_repo.get_by_id(spike_id, partition_key)
    if not spike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spike {spike_id} not found",
        )

    return SpikeDetail(
        id=spike.id,
        product=spike.product,
        region=spike.region,
        detected_at=spike.detected_at,
        expected_count=spike.expected_count,
        actual_count=spike.actual_count,
        deviation_percent=spike.deviation_percent,
        severity=spike.severity,
        status=spike.status.value,
        acknowledged_by=spike.acknowledged_by,
        acknowledged_at=spike.acknowledged_at,
        resolved_by=spike.resolved_by,
        resolved_at=spike.resolved_at,
        resolution_notes=spike.resolution_notes,
        baseline_mean=spike.baseline_mean,
        baseline_std=spike.baseline_std,
    )


@router.post(
    "/{spike_id}/acknowledge",
    response_model=SpikeResponse,
    summary="Acknowledge spike",
    description="Acknowledge a spike alert.",
    responses={
        404: {"description": "Spike not found"},
        400: {"description": "Invalid state"},
    },
)
async def acknowledge_spike(
    spike_id: UUID,
    request: SpikeAcknowledgeRequest,
    spike_repo: SpikeRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> SpikeResponse:
    """Acknowledge a spike alert."""
    partition_key = f"{region}|{month}"

    spike = await spike_repo.get_by_id(spike_id, partition_key)
    if not spike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spike {spike_id} not found",
        )

    if spike.status != SpikeStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spike is {spike.status.value}, cannot acknowledge",
        )

    # Use user from request if provided, otherwise current user
    acknowledged_by = request.acknowledged_by or current_user

    updated = await spike_repo.acknowledge(
        spike_id,
        partition_key,
        acknowledged_by=acknowledged_by,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge spike",
        )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="spike",
        entity_id=spike_id,
        action=AuditAction.SPIKE_ACKNOWLEDGED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        changes={
            "status": {"before": SpikeStatus.ACTIVE.value, "after": SpikeStatus.ACKNOWLEDGED.value},
        },
    )

    return SpikeResponse(
        id=updated.id,
        product=updated.product,
        region=updated.region,
        detected_at=updated.detected_at,
        expected_count=updated.expected_count,
        actual_count=updated.actual_count,
        deviation_percent=updated.deviation_percent,
        severity=updated.severity,
        status=updated.status.value,
    )


@router.post(
    "/{spike_id}/resolve",
    response_model=SpikeResponse,
    summary="Resolve spike",
    description="Mark a spike alert as resolved.",
    responses={
        404: {"description": "Spike not found"},
        400: {"description": "Invalid state"},
    },
)
async def resolve_spike(
    spike_id: UUID,
    request: SpikeResolveRequest,
    spike_repo: SpikeRepoDep,
    audit_repo: AuditRepoDep,
    current_user: CurrentUserDep,
    request_context: RequestContextDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> SpikeResponse:
    """Resolve a spike alert."""
    partition_key = f"{region}|{month}"

    spike = await spike_repo.get_by_id(spike_id, partition_key)
    if not spike:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spike {spike_id} not found",
        )

    if spike.status == SpikeStatus.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spike is already resolved",
        )

    resolved_by = request.resolved_by or current_user

    updated = await spike_repo.resolve(
        spike_id,
        partition_key,
        resolved_by=resolved_by,
        resolution_notes=request.resolution_notes,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve spike",
        )

    # Create audit entry
    await audit_repo.log_action(
        entity_type="spike",
        entity_id=spike_id,
        action=AuditAction.SPIKE_RESOLVED,
        user_id=current_user,
        user_ip=request_context.get("user_ip"),
        user_agent=request_context.get("user_agent"),
        changes={
            "status": {"before": spike.status.value, "after": SpikeStatus.RESOLVED.value},
            "resolution_notes": request.resolution_notes,
        },
    )

    return SpikeResponse(
        id=updated.id,
        product=updated.product,
        region=updated.region,
        detected_at=updated.detected_at,
        expected_count=updated.expected_count,
        actual_count=updated.actual_count,
        deviation_percent=updated.deviation_percent,
        severity=updated.severity,
        status=updated.status.value,
    )


@router.get(
    "/active/count",
    summary="Get active spike count",
    description="Get the count of active spike alerts.",
)
async def get_active_count(
    spike_repo: SpikeRepoDep,
    _api_key: ApiKeyDep,
    region: Annotated[str | None, Query(description="Region filter")] = None,
    month: Annotated[str | None, Query(description="Month filter")] = None,
) -> dict[str, int]:
    """Get count of active spikes."""
    partition_key = f"{region}|{month}" if region and month else None
    count = await spike_repo.get_active_count(partition_key)
    return {"active_count": count}
