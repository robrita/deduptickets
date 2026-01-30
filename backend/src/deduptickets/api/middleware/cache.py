"""
Response caching middleware for list endpoints.

Adds Cache-Control headers to improve performance and reduce redundant requests.
"""

from collections.abc import Callable
from typing import ClassVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware that adds caching headers to GET requests for list endpoints."""

    # Endpoints that should have caching headers
    CACHEABLE_PATTERNS: ClassVar[list[str]] = [
        "/clusters",
        "/tickets",
        "/merges",
        "/spikes",
        "/trends",
        "/audit",
    ]

    # Cache durations in seconds
    DEFAULT_MAX_AGE: int = 60  # 1 minute for list endpoints
    TRENDS_MAX_AGE: int = 300  # 5 minutes for trend data
    AUDIT_MAX_AGE: int = 30  # 30 seconds for audit (more dynamic)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and add cache headers to response."""
        response = await call_next(request)

        # Only add cache headers to GET requests
        if request.method != "GET":
            return response

        path = request.url.path

        # Skip caching for specific item endpoints (detail views change more)
        if self._is_detail_endpoint(path):
            response.headers["Cache-Control"] = "no-cache"
            return response

        # Add cache headers for list endpoints
        for pattern in self.CACHEABLE_PATTERNS:
            if pattern in path:
                max_age = self._get_max_age(path)
                response.headers["Cache-Control"] = f"public, max-age={max_age}"
                response.headers["Vary"] = "Accept, Authorization"
                break

        return response

    def _is_detail_endpoint(self, path: str) -> bool:
        """Check if this is a detail endpoint (has ID segment)."""
        segments = path.strip("/").split("/")
        # Detail endpoints typically have pattern: /resource/{id}
        if len(segments) >= 2:
            # Check if second segment looks like an ID (UUID or similar)
            potential_id = segments[-1]
            # Common patterns: action endpoints, IDs
            action_keywords = ["acknowledge", "resolve", "revert", "dismiss"]
            if any(kw in potential_id for kw in action_keywords):
                return True
            # If it contains hyphens (UUID-like), it's likely a detail endpoint
            if len(potential_id) > 8 and "-" in potential_id:
                return True
        return False

    def _get_max_age(self, path: str) -> int:
        """Get appropriate cache duration based on endpoint type."""
        if "/trends" in path:
            return self.TRENDS_MAX_AGE
        if "/audit" in path:
            return self.AUDIT_MAX_AGE
        return self.DEFAULT_MAX_AGE


def add_no_cache_headers(response: Response) -> Response:
    """Utility to explicitly disable caching for a response."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def add_cache_headers(response: Response, max_age: int = 60) -> Response:
    """Utility to add cache headers to a response manually."""
    response.headers["Cache-Control"] = f"public, max-age={max_age}"
    response.headers["Vary"] = "Accept, Authorization"
    return response
