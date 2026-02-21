"""
FastAPI dependency injection container.

Provides repository and service instances with proper scoping.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from config import Settings, get_settings
from cosmos.client import cosmos_manager
from lib.embedding import EmbeddingService
from repositories import (
    ClusterRepository,
    MergeRepository,
    TicketRepository,
)
from services.clustering_service import ClusteringService
from services.merge_service import MergeService

# Singleton embedding service (lazy-init, no connection on startup)
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton EmbeddingService instance."""
    global _embedding_service  # noqa: PLW0603
    if _embedding_service is None:
        _embedding_service = EmbeddingService(get_settings())
    return _embedding_service


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


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
    """Get ticket repository instance. Triggers lazy Cosmos DB init on first call."""
    container = await cosmos_manager.get_container("tickets")
    return TicketRepository(container)


async def get_cluster_repository() -> ClusterRepository:
    """Get cluster repository instance. Triggers lazy Cosmos DB init on first call."""
    container = await cosmos_manager.get_container("clusters")
    return ClusterRepository(container)


async def get_merge_repository() -> MergeRepository:
    """Get merge repository instance. Triggers lazy Cosmos DB init on first call."""
    container = await cosmos_manager.get_container("merges")
    return MergeRepository(container)


# Type aliases for cleaner route signatures
TicketRepoDep = Annotated[TicketRepository, Depends(get_ticket_repository)]
ClusterRepoDep = Annotated[ClusterRepository, Depends(get_cluster_repository)]
MergeRepoDep = Annotated[MergeRepository, Depends(get_merge_repository)]


# Service dependencies
async def get_clustering_service(
    ticket_repo: Annotated[TicketRepository, Depends(get_ticket_repository)],
    cluster_repo: Annotated[ClusterRepository, Depends(get_cluster_repository)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> ClusteringService:
    """Get clustering service with injected repositories and embedding service."""
    return ClusteringService(ticket_repo, cluster_repo, embedding_service)


async def get_merge_service(
    ticket_repo: Annotated[TicketRepository, Depends(get_ticket_repository)],
    cluster_repo: Annotated[ClusterRepository, Depends(get_cluster_repository)],
    merge_repo: Annotated[MergeRepository, Depends(get_merge_repository)],
) -> MergeService:
    """Get merge service with injected repositories."""
    return MergeService(ticket_repo, cluster_repo, merge_repo)


ClusteringServiceDep = Annotated[ClusteringService, Depends(get_clustering_service)]
MergeServiceDep = Annotated[MergeService, Depends(get_merge_service)]
