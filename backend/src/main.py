"""
FastAPI application entry point with lifespan management.

Initializes Cosmos DB connection, registers routers, and provides health endpoints.
"""

from __future__ import annotations

import logging
import pathlib
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from cosmos.client import CosmosClientManager
from exceptions import register_exception_handlers
from routes import clusters, health, merges, tickets

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

FRONTEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _configure_logging(log_level: str) -> None:
    """Configure application logging level from settings."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(level)

    for logger_name in ("services", "routes", "repositories", "cosmos", "lib"):
        logging.getLogger(logger_name).setLevel(level)

    # Clamp noisy Azure SDK HTTP logs to WARNING+ regardless of app log level.
    for logger_name in (
        "azure",
        "azure.cosmos",
        "azure.cosmos._cosmos_http_logging_policy",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan.

    - Startup: Configure Cosmos DB settings (no network call).
    - Shutdown: Close Cosmos DB connection pool if connected.
    """
    settings = get_settings()

    # Startup — store settings only, connect lazily on first request
    logger.info("Starting DedupTickets API...")
    cosmos_manager = CosmosClientManager()
    cosmos_manager.configure(settings)

    yield

    # Shutdown
    logger.info("Shutting down DedupTickets API...")
    await cosmos_manager.close()
    logger.info("Cosmos DB client closed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    settings = get_settings()
    _configure_logging(settings.log_level)

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

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["Tickets"])
    app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["Clusters"])
    app.include_router(merges.router, prefix="/api/v1/merges", tags=["Merges"])

    # Register exception handlers
    register_exception_handlers(app)

    # Serve frontend static build (SPA) if available
    if FRONTEND_DIR.is_dir():
        assets_dir = FRONTEND_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str) -> FileResponse:
            normalized_path = full_path.lstrip("/")
            blocked_prefixes = ("api/", "assets/", "health/")
            blocked_exact_paths = {"api", "docs", "redoc", "openapi.json", "health", "assets"}

            if normalized_path in blocked_exact_paths or normalized_path.startswith(
                blocked_prefixes
            ):
                raise HTTPException(status_code=404, detail="Not Found")

            return FileResponse(FRONTEND_DIR / "index.html")

    return app


# Application instance
app = create_app()
