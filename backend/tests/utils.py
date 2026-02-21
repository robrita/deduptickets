"""
Test utilities for DedupTickets tests.

Provides helper functions and mock builders for testing.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock


def mock_async_iter(items: list[Any]) -> MagicMock:
    """Create a mock async iterator."""
    mock = MagicMock()

    async def async_gen():
        for item in items:
            yield item

    mock.__aiter__ = lambda _: async_gen()
    return mock


def mock_repository_query(items: list[Any]) -> AsyncMock:
    """Create a mock repository query method returning items."""
    async_mock = AsyncMock()

    mock_iter = MagicMock()

    async def async_gen():
        for item in items:
            yield item

    mock_iter.__aiter__ = lambda _: async_gen()
    async_mock.return_value = mock_iter

    return async_mock


class MockContainerProxy:
    """Mock Cosmos container proxy for testing."""

    def __init__(self, items: list[dict[str, Any]] | None = None):
        self.items: dict[str, dict[str, Any]] = {}
        if items:
            for item in items:
                self.items[item["id"]] = item

    async def create_item(
        self,
        body: dict[str, Any],
        *,
        enable_automatic_id_generation: bool = False,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Mock create item."""
        self.items[body["id"]] = body
        return body

    async def read_item(
        self,
        item: str,
        partition_key: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Mock read item."""
        if item not in self.items:
            from azure.cosmos.exceptions import CosmosResourceNotFoundError  # noqa: PLC0415

            raise CosmosResourceNotFoundError(message="Not found")
        return self.items[item]

    async def upsert_item(self, body: dict[str, Any]) -> dict[str, Any]:
        """Mock upsert item."""
        self.items[body["id"]] = body
        return body

    async def delete_item(self, item: str, partition_key: str) -> None:  # noqa: ARG002
        """Mock delete item."""
        if item in self.items:
            del self.items[item]

    def query_items(
        self,
        query: str,  # noqa: ARG002
        parameters: list[dict[str, Any]] | None = None,  # noqa: ARG002
        partition_key: str | None = None,  # noqa: ARG002
        max_item_count: int = 100,
    ) -> MagicMock:
        """Mock query items - returns all items."""
        items = list(self.items.values())[:max_item_count]
        return mock_async_iter(items)


def assert_response_ok(response: Any, expected_status: int = 200) -> None:
    """Assert response is successful."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.json()}"
    )


def assert_response_error(
    response: Any,
    expected_status: int,
    expected_error: str | None = None,
) -> None:
    """Assert response is an error with expected status."""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}"
    )
    if expected_error:
        data = response.json()
        assert data.get("error") == expected_error or expected_error in data.get("message", "")
