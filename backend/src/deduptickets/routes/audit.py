"""
Audit log endpoints.

Provides read-only access to audit trail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, HTTPException, Query, status

from deduptickets.schemas.audit import (
    AuditListResponse,
    AuditResponse,
    AuditSearchParams,
)
from deduptickets.schemas.common import PaginationMeta

if TYPE_CHECKING:
    from uuid import UUID

    from deduptickets.dependencies import ApiKeyDep, AuditRepoDep
    from deduptickets.models.audit_entry import AuditAction

router = APIRouter()


@router.get(
    "",
    response_model=AuditListResponse,
    summary="List audit entries",
    description="List audit log entries with filtering.",
)
async def list_audit_entries(
    audit_repo: AuditRepoDep,
    _api_key: ApiKeyDep,
    entity_type: Annotated[str | None, Query(description="Entity type filter")] = None,
    month: Annotated[str | None, Query(description="Month in YYYY-MM format")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: Annotated[str | None, Query(description="User ID filter")] = None,
    action: Annotated[AuditAction | None, Query(description="Action filter")] = None,
) -> AuditListResponse:
    """List audit entries with filtering."""
    partition_key = f"{entity_type}|{month}" if entity_type and month else None

    if user_id:
        entries = await audit_repo.get_by_user(user_id, partition_key, limit=page_size)
    elif action:
        entries = await audit_repo.get_by_action(action, partition_key, limit=page_size)
    else:
        entries = await audit_repo.get_recent_entries(partition_key, hours=168, limit=page_size)

    items = [
        AuditResponse(
            id=e.id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action.value,
            user_id=e.user_id,
            timestamp=e.timestamp,
            user_ip=e.user_ip,
            changes=e.changes,
        )
        for e in entries
    ]

    return AuditListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )


@router.get(
    "/{audit_id}",
    response_model=AuditResponse,
    summary="Get audit entry",
    description="Get a specific audit log entry.",
    responses={
        404: {"description": "Audit entry not found"},
    },
)
async def get_audit_entry(
    audit_id: UUID,
    audit_repo: AuditRepoDep,
    _api_key: ApiKeyDep,
    entity_type: Annotated[str, Query(description="Entity type for partition key")],
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> AuditResponse:
    """Get an audit entry by ID."""
    partition_key = f"{entity_type}|{month}"

    entry = await audit_repo.get_by_id(audit_id, partition_key)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit entry {audit_id} not found",
        )

    return AuditResponse(
        id=entry.id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        action=entry.action.value,
        user_id=entry.user_id,
        timestamp=entry.timestamp,
        user_ip=entry.user_ip,
        changes=entry.changes,
    )


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=AuditListResponse,
    summary="Get entity history",
    description="Get audit history for a specific entity.",
)
async def get_entity_history(
    entity_type: str,
    entity_id: UUID,
    audit_repo: AuditRepoDep,
    _api_key: ApiKeyDep,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditListResponse:
    """Get audit history for an entity."""
    partition_key = f"{entity_type}|{month}"

    entries = await audit_repo.get_by_entity(entity_type, entity_id, partition_key, limit=page_size)

    items = [
        AuditResponse(
            id=e.id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action.value,
            user_id=e.user_id,
            timestamp=e.timestamp,
            user_ip=e.user_ip,
            changes=e.changes,
        )
        for e in entries
    ]

    return AuditListResponse(
        items=items,
        pagination=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )


@router.post(
    "/search",
    response_model=AuditListResponse,
    summary="Search audit entries",
    description="Advanced search across audit entries.",
)
async def search_audit_entries(
    search_params: AuditSearchParams,
    audit_repo: AuditRepoDep,
    _api_key: ApiKeyDep,
) -> AuditListResponse:
    """Search audit entries with multiple filters."""
    partition_key = None
    if search_params.entity_type and search_params.from_date:
        partition_key = f"{search_params.entity_type}|{search_params.from_date.strftime('%Y-%m')}"

    entries = await audit_repo.search(
        entity_type=search_params.entity_type,
        entity_id=search_params.entity_id,
        user_id=search_params.user_id,
        action=search_params.action,
        from_date=search_params.from_date,
        to_date=search_params.to_date,
        partition_key=partition_key,
        limit=search_params.page_size,
    )

    items = [
        AuditResponse(
            id=e.id,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            action=e.action.value,
            user_id=e.user_id,
            timestamp=e.timestamp,
            user_ip=e.user_ip,
            changes=e.changes,
        )
        for e in entries
    ]

    return AuditListResponse(
        items=items,
        pagination=PaginationMeta(
            page=search_params.page,
            page_size=search_params.page_size,
            total_items=len(items),
            total_pages=1,
        ),
    )
