"""
Audit middleware for automatic request logging.

Captures request/response information for audit trail.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log API requests for audit purposes.

    Captures:
    - Request path and method
    - User ID from headers
    - Response status and duration
    - Request correlation ID
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize audit middleware."""
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """
        Process request and log audit information.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware/handler in chain.

        Returns:
            HTTP response.
        """
        # Skip health checks
        if request.url.path in ("/health", "/health/ready"):
            return await call_next(request)

        # Generate correlation ID
        correlation_id = str(uuid4())
        request.state.correlation_id = correlation_id

        # Extract request metadata
        user_id = request.headers.get("X-User-ID", "anonymous")
        user_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        # Store in request state for route handlers
        request.state.user_id = user_id
        request.state.user_ip = user_ip
        request.state.user_agent = user_agent

        # Track timing
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log audit entry
        logger.info(
            "API Request | %s %s | user=%s | status=%d | duration=%.2fms | correlation_id=%s",
            request.method,
            request.url.path,
            user_id,
            response.status_code,
            duration_ms,
            correlation_id,
        )

        # Log warning for slow requests (Constitution: p95 < 300ms)
        if duration_ms > 300:
            logger.warning(
                "Slow request detected | %s %s | duration=%.2fms | correlation_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                correlation_id,
            )

        return response


def get_correlation_id(request: Request) -> str | None:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", None)


def get_user_context(request: Request) -> dict[str, str | None]:
    """Get user context from request state."""
    return {
        "user_id": getattr(request.state, "user_id", None),
        "user_ip": getattr(request.state, "user_ip", None),
        "user_agent": getattr(request.state, "user_agent", None),
    }
