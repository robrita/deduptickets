"""
Unit tests for the CacheMiddleware and cache utility functions.

Tests cover:
- Non-GET requests pass through without cache headers
- GET requests to list endpoints get public cache headers
- GET requests to detail endpoints get no-cache headers
- Action-keyword URLs get no-cache headers
- Utility functions add_no_cache_headers and add_cache_headers
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from starlette.responses import Response

from api.middleware.cache import CacheMiddleware, add_cache_headers, add_no_cache_headers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_request(method: str, path: str) -> MagicMock:
    req = MagicMock()
    req.method = method
    req.url.path = path
    return req


async def _call_next_200(_request: object) -> Response:
    """Stub call_next that returns a plain 200 response."""
    return Response(content="ok", status_code=200)


# ---------------------------------------------------------------------------
# Tests: CacheMiddleware.dispatch
# ---------------------------------------------------------------------------


class TestCacheMiddlewareDispatch:
    async def test_post_request_no_cache_header(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("POST", "/tickets")
        response = await middleware.dispatch(request, _call_next_200)
        assert "cache-control" not in response.headers

    async def test_put_request_no_cache_header(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("PUT", "/clusters/123")
        response = await middleware.dispatch(request, _call_next_200)
        assert "cache-control" not in response.headers

    async def test_delete_request_no_cache_header(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("DELETE", "/merges/abc")
        response = await middleware.dispatch(request, _call_next_200)
        assert "cache-control" not in response.headers

    async def test_get_list_tickets_public_cache(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/tickets")
        response = await middleware.dispatch(request, _call_next_200)
        assert "public, max-age=60" in response.headers.get("cache-control", "")
        assert "vary" in response.headers

    async def test_get_list_clusters_public_cache(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/clusters")
        response = await middleware.dispatch(request, _call_next_200)
        assert "public" in response.headers.get("cache-control", "")

    async def test_get_list_merges_public_cache(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/merges")
        response = await middleware.dispatch(request, _call_next_200)
        assert "public" in response.headers.get("cache-control", "")

    async def test_get_detail_uuid_no_cache(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/tickets/550e8400-e29b-41d4-a716-446655440000")
        response = await middleware.dispatch(request, _call_next_200)
        assert response.headers.get("cache-control") == "no-cache"

    async def test_get_health_no_cache_header_added(self) -> None:
        """Health endpoint is not in CACHEABLE_PATTERNS — no header added."""
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/health")
        response = await middleware.dispatch(request, _call_next_200)
        # Neither public nor no-cache should be set
        assert "public" not in response.headers.get("cache-control", "")

    async def test_get_action_endpoint_no_cache(self) -> None:
        """Endpoints with action keywords should get no-cache."""
        middleware = CacheMiddleware(app=AsyncMock())
        for action in ["acknowledge", "resolve", "revert", "dismiss"]:
            request = _mock_request("GET", f"/clusters/123/{action}")
            response = await middleware.dispatch(request, _call_next_200)
            assert response.headers.get("cache-control") == "no-cache", (
                f"Expected no-cache for action: {action}"
            )

    async def test_vary_header_on_list_endpoint(self) -> None:
        middleware = CacheMiddleware(app=AsyncMock())
        request = _mock_request("GET", "/tickets")
        response = await middleware.dispatch(request, _call_next_200)
        assert "Authorization" in response.headers.get("vary", "")


# ---------------------------------------------------------------------------
# Tests: CacheMiddleware._is_detail_endpoint
# ---------------------------------------------------------------------------


class TestIsDetailEndpoint:
    def _mw(self) -> CacheMiddleware:
        return CacheMiddleware(app=AsyncMock())

    def test_uuid_path_is_detail(self) -> None:
        mw = self._mw()
        assert mw._is_detail_endpoint("/tickets/550e8400-e29b-41d4-a716-446655440000") is True

    def test_list_path_is_not_detail(self) -> None:
        mw = self._mw()
        assert mw._is_detail_endpoint("/tickets") is False

    def test_action_keyword_is_detail(self) -> None:
        mw = self._mw()
        assert mw._is_detail_endpoint("/clusters/abc/dismiss") is True

    def test_shallow_path_is_not_detail(self) -> None:
        mw = self._mw()
        assert mw._is_detail_endpoint("/health") is False

    def test_short_segment_not_uuid_is_not_detail(self) -> None:
        mw = self._mw()
        # Only 6 chars, no hyphens → not considered UUID-like
        assert mw._is_detail_endpoint("/tickets/abc123") is False


# ---------------------------------------------------------------------------
# Tests: add_no_cache_headers
# ---------------------------------------------------------------------------


class TestAddNoCacheHeaders:
    def test_sets_no_store(self) -> None:
        r = Response()
        r = add_no_cache_headers(r)
        cc = r.headers.get("cache-control", "")
        assert "no-store" in cc
        assert "no-cache" in cc
        assert "must-revalidate" in cc

    def test_sets_pragma(self) -> None:
        r = Response()
        r = add_no_cache_headers(r)
        assert r.headers.get("pragma") == "no-cache"

    def test_sets_expires_zero(self) -> None:
        r = Response()
        r = add_no_cache_headers(r)
        assert r.headers.get("expires") == "0"

    def test_returns_same_response_object(self) -> None:
        r = Response()
        result = add_no_cache_headers(r)
        assert result is r


# ---------------------------------------------------------------------------
# Tests: add_cache_headers
# ---------------------------------------------------------------------------


class TestAddCacheHeaders:
    def test_default_max_age(self) -> None:
        r = Response()
        r = add_cache_headers(r)
        assert "public, max-age=60" in r.headers.get("cache-control", "")

    def test_custom_max_age(self) -> None:
        r = Response()
        r = add_cache_headers(r, max_age=300)
        assert "max-age=300" in r.headers.get("cache-control", "")

    def test_sets_vary(self) -> None:
        r = Response()
        r = add_cache_headers(r)
        assert "Authorization" in r.headers.get("vary", "")

    def test_returns_same_response_object(self) -> None:
        r = Response()
        result = add_cache_headers(r)
        assert result is r
