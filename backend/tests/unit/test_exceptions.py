"""
Unit tests for custom exception classes and exception handlers.

Validates that each exception class produces the correct message/status_code,
and that each handler returns the expected JSONResponse structure.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from fastapi import HTTPException

from exceptions import (
    DedupTicketsError,
    DuplicateEntityError,
    EntityNotFoundError,
    InvalidOperationError,
    RevertConflictError,
    cosmos_error_handler,
    cosmos_not_found_handler,
    deduptickets_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    register_exception_handlers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(path: str = "/test/path") -> MagicMock:
    """Build a minimal mock Request with a .url.path attribute."""
    req = MagicMock()
    req.url.path = path
    return req


# ---------------------------------------------------------------------------
# Exception class construction
# ---------------------------------------------------------------------------


class TestExceptionClasses:
    def test_entity_not_found_message(self) -> None:
        exc = EntityNotFoundError("Ticket", "abc-123")
        assert "Ticket" in exc.message
        assert "abc-123" in exc.message
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"

    def test_duplicate_entity_message(self) -> None:
        exc = DuplicateEntityError("Ticket", "TKT-001")
        assert "TKT-001" in exc.message
        assert exc.status_code == 409
        assert exc.error_code == "DUPLICATE"

    def test_invalid_operation_message(self) -> None:
        exc = InvalidOperationError("Cannot merge dismissed cluster")
        assert "Cannot merge dismissed cluster" in exc.message
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_OPERATION"

    def test_revert_conflict_message(self) -> None:
        exc = RevertConflictError(["merge-1", "merge-2"])
        assert "merge-1" in exc.message
        assert "merge-2" in exc.message
        assert exc.status_code == 409
        assert exc.error_code == "REVERT_CONFLICT"
        assert exc.conflict_ids == ["merge-1", "merge-2"]

    def test_base_exception_defaults(self) -> None:
        exc = DedupTicketsError("base error")
        assert exc.message == "base error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"

    def test_exception_is_str_representable(self) -> None:
        exc = EntityNotFoundError("Cluster", "id-xyz")
        assert str(exc) == exc.message

    def test_revert_conflict_empty_list(self) -> None:
        exc = RevertConflictError([])
        assert exc.conflict_ids == []


# ---------------------------------------------------------------------------
# deduptickets_exception_handler
# ---------------------------------------------------------------------------


class TestDedupTicketsExceptionHandler:
    async def test_returns_json_response(self) -> None:
        req = _make_request("/api/tickets")
        exc = EntityNotFoundError("Ticket", "id-1")
        response = await deduptickets_exception_handler(req, exc)
        assert response.status_code == 404
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "NOT_FOUND"
        assert "id-1" in body["message"]
        assert body["path"] == "/api/tickets"

    async def test_returns_500_for_base_error(self) -> None:
        req = _make_request("/clusters")
        exc = DedupTicketsError("internal failure")
        response = await deduptickets_exception_handler(req, exc)
        assert response.status_code == 500

    async def test_returns_409_for_duplicate_entity(self) -> None:
        req = _make_request("/tickets")
        exc = DuplicateEntityError("Ticket", "TKT-999")
        response = await deduptickets_exception_handler(req, exc)
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# http_exception_handler
# ---------------------------------------------------------------------------


class TestHttpExceptionHandler:
    async def test_404_http_exception(self) -> None:
        req = _make_request("/missing")
        exc = HTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(req, exc)
        assert response.status_code == 404
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "HTTP_ERROR"
        assert body["message"] == "Not found"
        assert body["path"] == "/missing"

    async def test_403_with_headers(self) -> None:
        req = _make_request("/admin")
        exc = HTTPException(
            status_code=403,
            detail="Forbidden",
            headers={"WWW-Authenticate": "Bearer"},
        )
        response = await http_exception_handler(req, exc)
        assert response.status_code == 403
        assert response.headers.get("www-authenticate") == "Bearer"

    async def test_500_http_exception(self) -> None:
        req = _make_request("/crash")
        exc = HTTPException(status_code=500, detail="Server Error")
        response = await http_exception_handler(req, exc)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# cosmos_not_found_handler
# ---------------------------------------------------------------------------


class TestCosmosNotFoundHandler:
    async def test_returns_404(self) -> None:
        req = _make_request("/clusters/missing-id")
        exc = CosmosResourceNotFoundError(message="404, Resource Not Found")
        response = await cosmos_not_found_handler(req, exc)
        assert response.status_code == 404
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "NOT_FOUND"
        assert body["path"] == "/clusters/missing-id"


# ---------------------------------------------------------------------------
# cosmos_error_handler
# ---------------------------------------------------------------------------


class TestCosmosErrorHandler:
    def _make_cosmos_error(self, status_code: int) -> CosmosHttpResponseError:
        exc = MagicMock(spec=CosmosHttpResponseError)
        exc.status_code = status_code
        exc.message = f"Cosmos error {status_code}"
        return exc  # type: ignore[return-value]

    async def test_409_conflict(self) -> None:
        req = _make_request("/merges")
        exc = self._make_cosmos_error(409)
        response = await cosmos_error_handler(req, exc)
        assert response.status_code == 409
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "CONFLICT"

    async def test_429_rate_limited(self) -> None:
        req = _make_request("/tickets")
        exc = self._make_cosmos_error(429)
        response = await cosmos_error_handler(req, exc)
        assert response.status_code == 429
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "RATE_LIMITED"
        assert "Retry-After" in response.headers

    async def test_503_for_other_status(self) -> None:
        req = _make_request("/clusters")
        exc = self._make_cosmos_error(500)
        response = await cosmos_error_handler(req, exc)
        assert response.status_code == 503
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "DATABASE_ERROR"

    async def test_400_falls_through_to_503(self) -> None:
        req = _make_request("/tickets")
        exc = self._make_cosmos_error(400)
        response = await cosmos_error_handler(req, exc)
        assert response.status_code == 503


# ---------------------------------------------------------------------------
# generic_exception_handler
# ---------------------------------------------------------------------------


class TestGenericExceptionHandler:
    async def test_returns_500(self) -> None:
        req = _make_request("/api/unknown")
        exc = RuntimeError("Totally unexpected")
        response = await generic_exception_handler(req, exc)
        assert response.status_code == 500
        import json  # noqa: PLC0415

        body = json.loads(response.body)
        assert body["error"] == "INTERNAL_ERROR"
        assert body["path"] == "/api/unknown"

    async def test_returns_500_for_value_error(self) -> None:
        req = _make_request("/merge")
        exc = ValueError("bad value")
        response = await generic_exception_handler(req, exc)
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# register_exception_handlers
# ---------------------------------------------------------------------------


class TestRegisterExceptionHandlers:
    def test_registers_without_error(self) -> None:
        """Calling register_exception_handlers must not raise."""
        app = MagicMock()
        register_exception_handlers(app)
        # Expect at least 5 handlers registered
        assert app.add_exception_handler.call_count >= 5

    def test_registers_dedup_tickets_error(self) -> None:
        app = MagicMock()
        register_exception_handlers(app)
        registered_types = [call.args[0] for call in app.add_exception_handler.call_args_list]
        assert DedupTicketsError in registered_types

    def test_registers_cosmos_error(self) -> None:
        app = MagicMock()
        register_exception_handlers(app)
        registered_types = [call.args[0] for call in app.add_exception_handler.call_args_list]
        assert CosmosHttpResponseError in registered_types
