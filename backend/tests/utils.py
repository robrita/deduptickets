"""
Test utilities for DedupTickets tests.

Provides helper functions and mock builders for testing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from deduptickets.models.cluster import Cluster, ClusterStatus
from deduptickets.models.merge_operation import MergeOperation, MergeStatus
from deduptickets.models.spike_alert import SpikeAlert, SpikeStatus
from deduptickets.models.ticket import Ticket


def create_mock_ticket(
    *,
    ticket_id: UUID | None = None,
    source_id: str | None = None,
    title: str = "Test Ticket",
    description: str = "Test description",
    product: str = "test-product",
    region: str = "us-east",
    severity: str = "medium",
    cluster_id: UUID | None = None,
) -> Ticket:
    """Create a mock ticket for testing."""
    now = datetime.utcnow()
    pk = f"{region}|{now.strftime('%Y-%m')}"

    return Ticket(
        id=ticket_id or uuid4(),
        source_id=source_id or f"SRC-{uuid4().hex[:8]}",
        source_system="test-system",
        title=title,
        description=description,
        severity=severity,
        product=product,
        region=region,
        cluster_id=cluster_id,
        created_at=now,
        pk=pk,
    )


def create_mock_cluster(
    *,
    cluster_id: UUID | None = None,
    ticket_ids: list[UUID] | None = None,
    status: ClusterStatus = ClusterStatus.PENDING,
    confidence_score: float = 0.85,
    region: str = "us-east",
) -> Cluster:
    """Create a mock cluster for testing."""
    now = datetime.utcnow()
    pk = f"{region}|{now.strftime('%Y-%m')}"
    tids = ticket_ids or [uuid4(), uuid4()]

    return Cluster(
        id=cluster_id or uuid4(),
        ticket_ids=tids,
        ticket_count=len(tids),
        confidence_score=confidence_score,
        status=status,
        matching_fields=["product", "severity"],
        created_at=now,
        pk=pk,
    )


def create_mock_merge(
    *,
    merge_id: UUID | None = None,
    cluster_id: UUID | None = None,
    canonical_ticket_id: UUID | None = None,
    merged_ticket_ids: list[UUID] | None = None,
    status: MergeStatus = MergeStatus.COMPLETED,
    region: str = "us-east",
) -> MergeOperation:
    """Create a mock merge operation for testing."""
    now = datetime.utcnow()
    pk = f"{region}|{now.strftime('%Y-%m')}"

    return MergeOperation(
        id=merge_id or uuid4(),
        cluster_id=cluster_id or uuid4(),
        canonical_ticket_id=canonical_ticket_id or uuid4(),
        merged_ticket_ids=merged_ticket_ids or [uuid4()],
        merged_by="test-user",
        merged_at=now,
        status=status,
        revert_deadline=None,
        pk=pk,
    )


def create_mock_spike(
    *,
    spike_id: UUID | None = None,
    product: str = "test-product",
    region: str = "us-east",
    status: SpikeStatus = SpikeStatus.ACTIVE,
    deviation_percent: float = 250.0,
) -> SpikeAlert:
    """Create a mock spike alert for testing."""
    now = datetime.utcnow()
    pk = f"{region}|{now.strftime('%Y-%m')}"

    return SpikeAlert(
        id=spike_id or uuid4(),
        product=product,
        region=region,
        detected_at=now,
        expected_count=100.0,
        actual_count=350,
        deviation_percent=deviation_percent,
        severity="high",
        status=status,
        baseline_mean=100.0,
        baseline_std=25.0,
        pk=pk,
    )


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
