"""
Health check endpoints.

Provides liveness and readiness probes for container orchestration.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from deduptickets.cosmos.client import CosmosClientManager
from deduptickets.schemas.common import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Basic liveness check - returns OK if the service is running.",
)
async def health_check() -> HealthResponse:
    """
    Simple liveness probe.

    Returns OK if the FastAPI application is responding.
    Does not check external dependencies.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
    )


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Checks if the service and all dependencies are ready.",
    responses={
        503: {"description": "Service unavailable - dependencies not ready"},
    },
)
async def readiness_check() -> HealthResponse:
    """
    Readiness probe with dependency checks.

    Checks:
    - Cosmos DB connection health

    Returns OK only if all dependencies are healthy.
    """
    cosmos_healthy = await CosmosClientManager.health_check()

    if not cosmos_healthy:
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            details={"cosmos_db": "unavailable"},
        )

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        details={"cosmos_db": "connected"},
    )
