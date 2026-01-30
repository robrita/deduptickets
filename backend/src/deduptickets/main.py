"""
FastAPI application entry point with lifespan management.

Initializes Cosmos DB connection, registers routers, and provides health endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deduptickets.api.middleware.audit_middleware import AuditMiddleware
from deduptickets.config import get_settings
from deduptickets.cosmos.client import CosmosClientManager
from deduptickets.cosmos.setup import ensure_database_setup
from deduptickets.exceptions import register_exception_handlers
from deduptickets.routes import audit, clusters, health, merges, spikes, tickets, trends

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    - Startup: Initialize Cosmos DB client and ensure containers exist.
    - Shutdown: Close Cosmos DB connection pool.
    """
    settings = get_settings()

    # Startup
    logger.info("Starting DedupTickets API...")

    # Initialize Cosmos DB client
    await CosmosClientManager.initialize(
        endpoint=settings.cosmos_endpoint,
        credential=settings.cosmos_key,
        database_name=settings.cosmos_database,
    )
    logger.info("Cosmos DB client initialized")

    # Ensure database and containers exist
    await ensure_database_setup()
    logger.info("Database setup verified")

    yield

    # Shutdown
    logger.info("Shutting down DedupTickets API...")
    await CosmosClientManager.close()
    logger.info("Cosmos DB client closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="DedupTickets API",
        description="AI-powered duplicate ticket detection and management",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit middleware for request logging
    app.add_middleware(AuditMiddleware)

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["Tickets"])
    app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["Clusters"])
    app.include_router(merges.router, prefix="/api/v1/merges", tags=["Merges"])
    app.include_router(spikes.router, prefix="/api/v1/spikes", tags=["Spikes"])
    app.include_router(audit.router, prefix="/api/v1/audit", tags=["Audit"])
    app.include_router(trends.router, prefix="/api/v1/trends", tags=["Trends"])

    # Register exception handlers
    register_exception_handlers(app)

    return app


# Application instance
app = create_app()
