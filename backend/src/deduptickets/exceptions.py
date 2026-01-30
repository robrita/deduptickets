"""
Exception handlers and custom exceptions.

Provides consistent error responses across the API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exceptions
# =============================================================================


class DedupTicketsError(Exception):
    """Base exception for DedupTickets application."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class EntityNotFoundError(DedupTicketsError):
    """Entity was not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
        )


class DuplicateEntityError(DedupTicketsError):
    """Entity already exists."""

    def __init__(self, entity_type: str, identifier: str) -> None:
        super().__init__(
            message=f"{entity_type} '{identifier}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE",
        )


class InvalidOperationError(DedupTicketsError):
    """Operation is not valid in current state."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="INVALID_OPERATION",
        )


class RevertConflictError(DedupTicketsError):
    """Merge revert conflicts with subsequent operations."""

    def __init__(self, conflict_ids: list[str]) -> None:
        super().__init__(
            message=f"Revert conflicts with merges: {', '.join(conflict_ids)}",
            status_code=status.HTTP_409_CONFLICT,
            error_code="REVERT_CONFLICT",
        )
        self.conflict_ids = conflict_ids


# =============================================================================
# Exception Handlers
# =============================================================================


async def deduptickets_exception_handler(
    request: Request,
    exc: DedupTicketsError,
) -> JSONResponse:
    """Handle DedupTickets custom exceptions."""
    logger.warning(
        "Application error: %s - %s (path: %s)",
        exc.error_code,
        exc.message,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "path": request.url.path,
        },
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "path": request.url.path,
        },
        headers=exc.headers,
    )


async def validation_exception_handler(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "path": request.url.path,
        },
    )


async def cosmos_not_found_handler(
    request: Request,
    _exc: CosmosResourceNotFoundError,
) -> JSONResponse:
    """Handle Cosmos DB not found errors."""
    logger.warning("Cosmos resource not found: %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "NOT_FOUND",
            "message": "Resource not found",
            "path": request.url.path,
        },
    )


async def cosmos_error_handler(
    request: Request,
    exc: CosmosHttpResponseError,
) -> JSONResponse:
    """Handle Cosmos DB HTTP errors."""
    logger.error(
        "Cosmos DB error: status=%s, message=%s, path=%s",
        exc.status_code,
        exc.message,
        request.url.path,
    )

    # Map Cosmos status codes to HTTP
    if exc.status_code == 409:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "CONFLICT",
                "message": "Resource conflict",
                "path": request.url.path,
            },
        )

    if exc.status_code == 429:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMITED",
                "message": "Too many requests, please retry later",
                "path": request.url.path,
            },
            headers={"Retry-After": "1"},
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "DATABASE_ERROR",
            "message": "Database operation failed",
            "path": request.url.path,
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception("Unexpected error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "path": request.url.path,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(DedupTicketsError, deduptickets_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(CosmosResourceNotFoundError, cosmos_not_found_handler)
    app.add_exception_handler(CosmosHttpResponseError, cosmos_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
