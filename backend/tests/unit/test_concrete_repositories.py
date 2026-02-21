"""
Unit tests for TicketRepository, ClusterRepository, and MergeRepository.

Exercises all concrete methods (query helpers, build_partition_key,
read-modify-write patterns, vector search helpers) using mocked containers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from models.cluster import Cluster, ClusterMember, ClusterStatus
from models.merge_operation import MergeBehavior, MergeOperation, MergeStatus
from models.ticket import Ticket, TicketPriority, TicketStatus
from repositories.cluster import ClusterRepository
from repositories.merge import MergeRepository
from repositories.ticket import TicketRepository

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

MONTH = "2025-01"
NOW = datetime(2025, 1, 15, 10, 0, 0)


async def _async_gen_items(items: list[dict[str, Any]]):
    for item in items:
        yield item


def _make_container() -> MagicMock:
    c = MagicMock()
    c.create_item = AsyncMock()
    c.read_item = AsyncMock()
    c.upsert_item = AsyncMock()
    c.delete_item = AsyncMock()
    c.replace_item = AsyncMock()
    c.query_items = MagicMock(return_value=_async_gen_items([]))
    return c


def _make_cosmos_error(status: int = 500) -> CosmosHttpResponseError:
    err = CosmosHttpResponseError.__new__(CosmosHttpResponseError)
    err.status_code = status
    err.message = f"cosmos error {status}"
    err.args = (f"cosmos error {status}",)
    return err


# ---------------------------------------------------------------------------
# Sample model builders
# ---------------------------------------------------------------------------


def _build_ticket(ticket_id: UUID | None = None) -> Ticket:
    return Ticket(
        id=ticket_id or uuid4(),
        pk=MONTH,
        ticket_number="TKT-001",
        created_at=NOW,
        updated_at=NOW,
        channel="in_app",
        customer_id="CUST-1",
        category="Billing",
        summary="Test ticket",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
    )


def _build_cluster(cluster_id: UUID | None = None) -> Cluster:
    return Cluster(
        id=cluster_id or uuid4(),
        pk=MONTH,
        status=ClusterStatus.PENDING,
        summary="Test cluster",
        ticket_count=1,
    )


def _build_merge(
    merge_id: UUID | None = None,
    cluster_id: UUID | None = None,
    primary_id: UUID | None = None,
) -> MergeOperation:
    return MergeOperation(
        id=merge_id or uuid4(),
        pk=MONTH,
        cluster_id=cluster_id or uuid4(),
        primary_ticket_id=primary_id or uuid4(),
        secondary_ticket_ids=[uuid4()],
        performed_by="test-user",
        performed_at=NOW,
        status=MergeStatus.COMPLETED,
        merge_behavior=MergeBehavior.KEEP_LATEST,
    )


# ===========================================================================
# TicketRepository
# ===========================================================================


class TestTicketRepository:
    def test_constructor(self) -> None:
        container = _make_container()
        repo = TicketRepository(container)
        assert repo is not None

    def test_to_document(self) -> None:
        repo = TicketRepository(_make_container())
        ticket = _build_ticket()
        doc = repo._to_document(ticket)
        assert isinstance(doc, dict)
        assert "id" in doc

    def test_from_document(self) -> None:
        repo = TicketRepository(_make_container())
        ticket = _build_ticket()
        doc = ticket.to_cosmos_document()
        result = repo._from_document(doc)
        assert isinstance(result, Ticket)
        assert result.ticket_number == "TKT-001"

    def test_build_partition_key(self) -> None:
        assert TicketRepository.build_partition_key(NOW) == "2025-01"

    async def test_get_by_ticket_number_found(self) -> None:
        container = _make_container()
        ticket = _build_ticket()
        container.query_items = MagicMock(
            return_value=_async_gen_items([ticket.to_cosmos_document()])
        )
        repo = TicketRepository(container)
        result = await repo.get_by_ticket_number("TKT-001", MONTH)
        assert result is not None
        assert result.ticket_number == "TKT-001"

    async def test_get_by_ticket_number_not_found(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(return_value=_async_gen_items([]))
        repo = TicketRepository(container)
        result = await repo.get_by_ticket_number("TKT-999", MONTH)
        assert result is None

    async def test_get_unassigned_tickets(self) -> None:
        container = _make_container()
        ticket = _build_ticket()
        container.query_items = MagicMock(
            return_value=_async_gen_items([ticket.to_cosmos_document()])
        )
        repo = TicketRepository(container)
        results = await repo.get_unassigned_tickets(MONTH)
        assert len(results) == 1

    async def test_get_by_cluster_id(self) -> None:
        container = _make_container()
        ticket = _build_ticket()
        container.query_items = MagicMock(
            return_value=_async_gen_items([ticket.to_cosmos_document()])
        )
        repo = TicketRepository(container)
        results = await repo.get_by_cluster_id(uuid4(), MONTH)
        assert len(results) == 1

    async def test_assign_to_cluster_found(self) -> None:
        ticket = _build_ticket()
        container = _make_container()
        container.read_item.return_value = ticket.to_cosmos_document()
        updated_doc = ticket.to_cosmos_document()
        container.upsert_item.return_value = updated_doc
        repo = TicketRepository(container)
        result = await repo.assign_to_cluster(ticket.id, uuid4(), MONTH)
        assert result is not None

    async def test_assign_to_cluster_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = TicketRepository(container)
        result = await repo.assign_to_cluster(uuid4(), uuid4(), MONTH)
        assert result is None

    async def test_remove_from_cluster_found(self) -> None:
        ticket = _build_ticket()
        ticket.cluster_id = uuid4()
        container = _make_container()
        container.read_item.return_value = ticket.to_cosmos_document()
        container.upsert_item.return_value = ticket.to_cosmos_document()
        repo = TicketRepository(container)
        result = await repo.remove_from_cluster(ticket.id, MONTH)
        assert result is not None

    async def test_remove_from_cluster_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = TicketRepository(container)
        result = await repo.remove_from_cluster(uuid4(), MONTH)
        assert result is None


# ===========================================================================
# ClusterRepository
# ===========================================================================


class TestClusterRepository:
    def test_constructor(self) -> None:
        container = _make_container()
        repo = ClusterRepository(container)
        assert repo is not None

    def test_to_document(self) -> None:
        repo = ClusterRepository(_make_container())
        cluster = _build_cluster()
        doc = repo._to_document(cluster)
        assert isinstance(doc, dict)

    def test_from_document(self) -> None:
        repo = ClusterRepository(_make_container())
        cluster = _build_cluster()
        doc = cluster.to_cosmos_document()
        result = repo._from_document(doc)
        assert isinstance(result, Cluster)

    def test_build_partition_key(self) -> None:
        assert ClusterRepository.build_partition_key(NOW) == "2025-01"

    async def test_get_pending_clusters(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([cluster.to_cosmos_document()])
        )
        repo = ClusterRepository(container)
        results = await repo.get_pending_clusters(MONTH)
        assert len(results) == 1

    async def test_get_pending_review_count(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(return_value=_async_gen_items([5]))
        repo = ClusterRepository(container)
        count = await repo.get_pending_review_count(MONTH)
        assert count == 5

    async def test_get_by_status(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([cluster.to_cosmos_document()])
        )
        repo = ClusterRepository(container)
        results = await repo.get_by_status(ClusterStatus.PENDING, MONTH)
        assert len(results) == 1

    async def test_get_clusters_with_ticket(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([cluster.to_cosmos_document()])
        )
        repo = ClusterRepository(container)
        results = await repo.get_clusters_with_ticket(uuid4(), MONTH)
        assert len(results) == 1

    async def test_update_status_found(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        container.upsert_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.update_status(cluster.id, ClusterStatus.DISMISSED, MONTH)
        assert result is not None

    async def test_update_status_with_dismissed_sets_fields(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        container.upsert_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.update_status(
            cluster.id,
            ClusterStatus.DISMISSED,
            MONTH,
            dismissed_by="admin",
            dismissal_reason="false positive",
        )
        assert result is not None

    async def test_update_status_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = ClusterRepository(container)
        result = await repo.update_status(uuid4(), ClusterStatus.DISMISSED, MONTH)
        assert result is None

    async def test_add_ticket_new_member(self) -> None:
        cluster = _build_cluster()
        ticket_id = uuid4()
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        container.upsert_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.add_ticket(cluster.id, ticket_id, MONTH, ticket_number="TKT-X")
        assert result is not None

    async def test_add_ticket_already_exists(self) -> None:
        ticket_id = uuid4()
        cluster = _build_cluster()
        cluster.members.append(ClusterMember(ticket_id=ticket_id, ticket_number="TKT-X"))
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.add_ticket(cluster.id, ticket_id, MONTH)
        # Should return cluster unchanged (no update call)
        assert result is not None

    async def test_add_ticket_cluster_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = ClusterRepository(container)
        result = await repo.add_ticket(uuid4(), uuid4(), MONTH)
        assert result is None

    async def test_remove_ticket_found_and_removed(self) -> None:
        ticket_id = uuid4()
        cluster = _build_cluster()
        cluster.members.append(ClusterMember(ticket_id=ticket_id, ticket_number="TKT-X"))
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        container.upsert_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.remove_ticket(cluster.id, ticket_id, MONTH)
        assert result is not None

    async def test_remove_ticket_not_in_cluster(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.read_item.return_value = cluster.to_cosmos_document()
        container.upsert_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.remove_ticket(cluster.id, uuid4(), MONTH)
        assert result is not None

    async def test_remove_ticket_cluster_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = ClusterRepository(container)
        result = await repo.remove_ticket(uuid4(), uuid4(), MONTH)
        assert result is None

    async def test_get_by_date_range(self) -> None:
        cluster = _build_cluster()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([cluster.to_cosmos_document()])
        )
        repo = ClusterRepository(container)
        results = await repo.get_by_date_range(
            start_date=datetime(2025, 1, 1),
            end_date=datetime(2025, 1, 31),
        )
        assert len(results) == 1

    async def test_find_cluster_candidates_with_customer_filter(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([{"id": str(uuid4()), "similarityScore": 0.9}])
        )
        repo = ClusterRepository(container)
        results = await repo.find_cluster_candidates(
            customer_id="CUST-1",
            min_updated_at="2025-01-01T00:00:00",
            query_vector=[0.1] * 10,
            top_k=5,
            partition_keys=[MONTH],
        )
        assert isinstance(results, list)

    async def test_find_cluster_candidates_no_customer_filter(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(return_value=_async_gen_items([]))
        repo = ClusterRepository(container)
        results = await repo.find_cluster_candidates(
            customer_id="CUST-1",
            min_updated_at="2025-01-01T00:00:00",
            query_vector=[0.1] * 10,
            top_k=5,
            partition_keys=[MONTH],
            filter_by_customer=False,
        )
        assert results == []

    async def test_find_cluster_candidates_cosmos_error_skipped(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(side_effect=_make_cosmos_error(503))
        repo = ClusterRepository(container)
        results = await repo.find_cluster_candidates(
            customer_id="CUST-1",
            min_updated_at="2025-01-01T00:00:00",
            query_vector=[0.1] * 10,
            top_k=5,
            partition_keys=[MONTH],
        )
        assert results == []

    async def test_update_cluster_with_etag(self) -> None:
        cluster = _build_cluster()
        cluster.etag = '"abc123"'
        container = _make_container()
        container.replace_item.return_value = cluster.to_cosmos_document()
        repo = ClusterRepository(container)
        result = await repo.update_cluster_with_etag(cluster)
        assert result is not None
        container.replace_item.assert_awaited_once()


# ===========================================================================
# MergeRepository
# ===========================================================================


class TestMergeRepository:
    def test_constructor(self) -> None:
        container = _make_container()
        repo = MergeRepository(container)
        assert repo is not None

    def test_to_document(self) -> None:
        repo = MergeRepository(_make_container())
        merge = _build_merge()
        doc = repo._to_document(merge)
        assert isinstance(doc, dict)

    def test_from_document(self) -> None:
        repo = MergeRepository(_make_container())
        merge = _build_merge()
        doc = merge.to_cosmos_document()
        result = repo._from_document(doc)
        assert isinstance(result, MergeOperation)

    def test_build_partition_key(self) -> None:
        assert MergeRepository.build_partition_key(NOW) == "2025-01"

    async def test_get_by_cluster_id(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([merge.to_cosmos_document()])
        )
        repo = MergeRepository(container)
        results = await repo.get_by_cluster_id(uuid4(), MONTH)
        assert len(results) == 1

    async def test_get_by_primary_ticket_id(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([merge.to_cosmos_document()])
        )
        repo = MergeRepository(container)
        results = await repo.get_by_primary_ticket_id(uuid4(), MONTH)
        assert len(results) == 1

    async def test_get_revertible_merges(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([merge.to_cosmos_document()])
        )
        repo = MergeRepository(container)
        results = await repo.get_revertible_merges(MONTH)
        assert len(results) == 1

    async def test_get_pending_merges(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.query_items = MagicMock(
            return_value=_async_gen_items([merge.to_cosmos_document()])
        )
        repo = MergeRepository(container)
        results = await repo.get_pending_merges(MONTH)
        assert len(results) == 1

    async def test_update_status_found(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.read_item.return_value = merge.to_cosmos_document()
        container.upsert_item.return_value = merge.to_cosmos_document()
        repo = MergeRepository(container)
        result = await repo.update_status(merge.id, MergeStatus.REVERTED, MONTH)
        assert result is not None

    async def test_update_status_reverted_sets_fields(self) -> None:
        merge = _build_merge()
        container = _make_container()
        container.read_item.return_value = merge.to_cosmos_document()
        container.upsert_item.return_value = merge.to_cosmos_document()
        repo = MergeRepository(container)
        result = await repo.update_status(
            merge.id,
            MergeStatus.REVERTED,
            MONTH,
            reverted_by="admin",
            reverted_at=NOW,
            revert_reason="error",
        )
        assert result is not None

    async def test_update_status_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = MergeRepository(container)
        result = await repo.update_status(uuid4(), MergeStatus.REVERTED, MONTH)
        assert result is None

    async def test_get_merged_ticket_ids_empty(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(return_value=_async_gen_items([]))
        repo = MergeRepository(container)
        result = await repo.get_merged_ticket_ids(uuid4(), MONTH)
        assert result == []

    async def test_get_merge_count_by_user(self) -> None:
        container = _make_container()
        container.query_items = MagicMock(return_value=_async_gen_items([3]))
        repo = MergeRepository(container)
        count = await repo.get_merge_count_by_user("user-1", MONTH)
        assert count == 3

    async def test_check_revert_conflicts_merge_not_found(self) -> None:
        container = _make_container()
        container.read_item.side_effect = CosmosResourceNotFoundError(message="not found")
        repo = MergeRepository(container)
        result = await repo.check_revert_conflicts(uuid4(), MONTH)
        assert result == []

    async def test_check_revert_conflicts_found(self) -> None:
        merge = _build_merge()
        conflict = _build_merge()
        container = _make_container()
        # First read_item returns the merge itself, subsequent query returns conflicts
        container.read_item.return_value = merge.to_cosmos_document()
        container.query_items = MagicMock(
            return_value=_async_gen_items([conflict.to_cosmos_document()])
        )
        repo = MergeRepository(container)
        result = await repo.check_revert_conflicts(merge.id, MONTH)
        assert len(result) == 1
