"""
FastAPI dependency injection container.

Provides repository and service instances with proper scoping.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from deduptickets.config import Settings, get_settings
from deduptickets.cosmos.client import CosmosClientManager
from deduptickets.repositories import (
    AuditRepository,
    BaselineRepository,
    ClusterRepository,
    MergeRepository,
    SpikeRepository,
    TicketRepository,
)


# Settings dependency
@lru_cache
def get_cached_settings() -> Settings:
    """Get cached settings instance."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_cached_settings)]


# API Key authentication
async def verify_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_cached_settings)] = None,  # type: ignore[assignment]
) -> str:
    """
    Verify API key from header.

    Args:
        x_api_key: API key from X-API-Key header.
        settings: Application settings.

    Returns:
        The validated API key.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.api_key.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


ApiKeyDep = Annotated[str, Depends(verify_api_key)]


# User context from request
async def get_current_user(request: Request) -> str:
    """
    Extract current user from request context.

    For MVP, uses API key as user identifier.
    In production, would extract from JWT or session.

    Args:
        request: FastAPI request object.

    Returns:
        User identifier string.
    """
    # For MVP, use a simple user identifier from header or default
    user_id = request.headers.get("X-User-ID", "system")
    return user_id


CurrentUserDep = Annotated[str, Depends(get_current_user)]


# Repository dependencies
async def get_ticket_repository() -> TicketRepository:
    """Get ticket repository instance."""
    container = await CosmosClientManager.get_container("tickets")
    return TicketRepository(container)


async def get_cluster_repository() -> ClusterRepository:
    """Get cluster repository instance."""
    container = await CosmosClientManager.get_container("clusters")
    return ClusterRepository(container)


async def get_merge_repository() -> MergeRepository:
    """Get merge repository instance."""
    container = await CosmosClientManager.get_container("merges")
    return MergeRepository(container)


async def get_audit_repository() -> AuditRepository:
    """Get audit repository instance."""
    container = await CosmosClientManager.get_container("audit")
    return AuditRepository(container)


async def get_spike_repository() -> SpikeRepository:
    """Get spike repository instance."""
    container = await CosmosClientManager.get_container("spikes")
    return SpikeRepository(container)


async def get_baseline_repository() -> BaselineRepository:
    """Get baseline repository instance."""
    container = await CosmosClientManager.get_container("baselines")
    return BaselineRepository(container)


# Type aliases for cleaner route signatures
TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repository)]
ClusterRepoDep = Annotated[ClusterRepository, Depends(get_cluster_repository)]
MergeRepoDep = Annotated[MergeRepository, Depends(get_merge_repository)]
AuditRepoDep = Annotated[AuditRepository, Depends(get_audit_repository)]
SpikeRepoDep = Annotated[SpikeRepository, Depends(get_spike_repository)]
BaselineRepoDep = Annotated[BaselineRepository, Depends(get_baseline_repository)]


# Request context for audit logging
async def get_request_context(request: Request) -> dict[str, str | None]:
    """
    Extract request context for audit logging.

    Args:
        request: FastAPI request object.

    Returns:
        Dictionary with user IP and user agent.
    """
    return {
        "user_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
    }


RequestContextDep = Annotated[dict[str, str | None], Depends(get_request_context)]
