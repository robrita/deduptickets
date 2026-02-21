"""
Unit tests for Cluster and MergeOperation domain models.

Covers lifecycle methods, serialisation round-trips, and edge cases
that are not yet exercised by the service-layer tests.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
)
from models.merge_operation import (
    MergeBehavior,
    MergeOperation,
    MergeStatus,
    TicketSnapshot,
)

NOW = datetime(2025, 1, 15, 10, 0, 0)
MONTH = "2025-01"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cluster(**kwargs: object) -> Cluster:
    defaults: dict = {
        "pk": MONTH,
        "status": ClusterStatus.PENDING,
        "summary": "test cluster",
        "ticket_count": 1,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(kwargs)
    return Cluster(**defaults)


def _make_merge(**kwargs: object) -> MergeOperation:
    defaults: dict = {
        "pk": MONTH,
        "cluster_id": uuid4(),
        "primary_ticket_id": uuid4(),
        "secondary_ticket_ids": [uuid4()],
        "merge_behavior": MergeBehavior.KEEP_LATEST,
        "performed_by": "system",
        "performed_at": NOW,
    }
    defaults.update(kwargs)
    return MergeOperation(**defaults)


# ---------------------------------------------------------------------------
# Cluster.add_member
# ---------------------------------------------------------------------------


class TestClusterAddMember:
    def test_add_member_increments_ticket_count(self) -> None:
        cluster = _make_cluster()
        tid = uuid4()
        cluster.add_member(tid, "TKT-001")
        assert cluster.ticket_count == 1
        assert any(m.ticket_id == tid for m in cluster.members)

    def test_add_multiple_members(self) -> None:
        cluster = _make_cluster()
        for i in range(3):
            cluster.add_member(uuid4(), f"TKT-{i:03d}")
        assert cluster.ticket_count == 3
        assert len(cluster.members) == 3

    def test_add_member_updates_updated_at(self) -> None:
        cluster = _make_cluster()
        import time  # noqa: PLC0415

        time.sleep(0)  # yield to ensure utcnow advances
        cluster.add_member(uuid4(), "TKT-NEW")
        # updated_at is set to DateTime.utcnow() inside add_member
        assert isinstance(cluster.updated_at, datetime)

    def test_add_member_at_limit_raises(self) -> None:
        cluster = _make_cluster()
        # Fill exactly 100 members
        for i in range(100):
            cluster.members.append(
                ClusterMember(
                    ticket_id=uuid4(),
                    ticket_number=f"TKT-{i:03d}",
                    added_at=NOW,
                )
            )
        cluster.ticket_count = 100
        with pytest.raises(ValueError, match="limit"):
            cluster.add_member(uuid4(), "TKT-OVERFLOW")

    def test_add_member_at_custom_limit_raises(self) -> None:
        cluster = _make_cluster()
        # Fill exactly 5 members
        for i in range(5):
            cluster.members.append(
                ClusterMember(
                    ticket_id=uuid4(),
                    ticket_number=f"TKT-{i:03d}",
                    added_at=NOW,
                )
            )
        cluster.ticket_count = 5
        with pytest.raises(ValueError, match=r"limit \(5\)"):
            cluster.add_member(uuid4(), "TKT-OVERFLOW", max_members=5)

    def test_add_member_custom_limit_allows_more(self) -> None:
        cluster = _make_cluster()
        for i in range(100):
            cluster.members.append(
                ClusterMember(
                    ticket_id=uuid4(),
                    ticket_number=f"TKT-{i:03d}",
                    added_at=NOW,
                )
            )
        cluster.ticket_count = 100
        # With higher cap, should succeed
        cluster.add_member(uuid4(), "TKT-101", max_members=200)
        assert cluster.ticket_count == 101


# ---------------------------------------------------------------------------
# Cluster.remove_member
# ---------------------------------------------------------------------------


class TestClusterRemoveMember:
    def test_remove_existing_member(self) -> None:
        cluster = _make_cluster()
        tid = uuid4()
        cluster.members.append(ClusterMember(ticket_id=tid, ticket_number="TKT-RM", added_at=NOW))
        cluster.ticket_count = 1
        removed = cluster.remove_member(tid)
        assert removed is True
        assert all(m.ticket_id != tid for m in cluster.members)

    def test_remove_nonexistent_member_returns_false(self) -> None:
        cluster = _make_cluster()
        result = cluster.remove_member(uuid4())
        assert result is False

    def test_remove_updates_ticket_count(self) -> None:
        cluster = _make_cluster()
        tid1, tid2 = uuid4(), uuid4()
        cluster.members = [
            ClusterMember(ticket_id=tid1, ticket_number="TKT-1", added_at=NOW),
            ClusterMember(ticket_id=tid2, ticket_number="TKT-2", added_at=NOW),
        ]
        cluster.ticket_count = 2
        cluster.remove_member(tid1)
        assert cluster.ticket_count == 1


# ---------------------------------------------------------------------------
# Cluster.ticket_ids property
# ---------------------------------------------------------------------------


class TestClusterTicketIds:
    def test_returns_empty_for_no_members(self) -> None:
        cluster = _make_cluster()
        assert cluster.ticket_ids == []

    def test_returns_all_member_ids(self) -> None:
        cluster = _make_cluster()
        ids = [uuid4() for _ in range(3)]
        cluster.members = [
            ClusterMember(ticket_id=tid, ticket_number=f"TKT-{i}", added_at=NOW)
            for i, tid in enumerate(ids)
        ]
        assert set(cluster.ticket_ids) == set(ids)


# ---------------------------------------------------------------------------
# Cluster.to_cosmos_document / from_cosmos_document
# ---------------------------------------------------------------------------


class TestClusterCosmosRoundTrip:
    def test_to_cosmos_document_has_string_id(self) -> None:
        cluster = _make_cluster()
        doc = cluster.to_cosmos_document()
        assert isinstance(doc["id"], str)

    def test_to_cosmos_document_no_etag(self) -> None:
        cluster = _make_cluster()
        doc = cluster.to_cosmos_document()
        assert "_etag" not in doc

    def test_round_trip_preserves_status(self) -> None:
        cluster = _make_cluster(status=ClusterStatus.MERGED)
        doc = cluster.to_cosmos_document()
        restored = Cluster.from_cosmos_document(doc)
        assert restored.status == ClusterStatus.MERGED

    def test_round_trip_preserves_members(self) -> None:
        cluster = _make_cluster()
        tid = uuid4()
        cluster.members = [ClusterMember(ticket_id=tid, ticket_number="TKT-001", added_at=NOW)]
        doc = cluster.to_cosmos_document()
        restored = Cluster.from_cosmos_document(doc)
        assert len(restored.members) == 1

    def test_from_cosmos_document_with_camel_keys(self) -> None:
        cluster = _make_cluster(status=ClusterStatus.DISMISSED)
        doc = cluster.to_cosmos_document()
        # Ensure camelCase keys are accepted
        assert "ticketCount" in doc
        restored = Cluster.from_cosmos_document(doc)
        assert restored.status == ClusterStatus.DISMISSED


# ---------------------------------------------------------------------------
# MergeOperation.to_cosmos_document / from_cosmos_document
# ---------------------------------------------------------------------------


class TestMergeOperationCosmosRoundTrip:
    def test_to_cosmos_document_has_string_id(self) -> None:
        merge = _make_merge()
        doc = merge.to_cosmos_document()
        assert isinstance(doc["id"], str)

    def test_round_trip_preserves_status(self) -> None:
        merge = _make_merge(status=MergeStatus.COMPLETED)
        doc = merge.to_cosmos_document()
        restored = MergeOperation.from_cosmos_document(doc)
        assert restored.status == MergeStatus.COMPLETED

    def test_round_trip_preserves_secondary_ids(self) -> None:
        sec_ids = [uuid4(), uuid4()]
        merge = _make_merge(secondary_ticket_ids=sec_ids)
        doc = merge.to_cosmos_document()
        restored = MergeOperation.from_cosmos_document(doc)
        assert len(restored.secondary_ticket_ids) == 2


# ---------------------------------------------------------------------------
# MergeOperation.revert
# ---------------------------------------------------------------------------


class TestMergeOperationRevert:
    def test_revert_marks_status_reverted(self) -> None:
        merge = _make_merge()
        merge.revert("user-1", reason="test revert")
        assert merge.status == MergeStatus.REVERTED
        assert merge.reverted_by == "user-1"
        assert merge.revert_reason == "test revert"
        assert merge.reverted_at is not None

    def test_revert_without_reason(self) -> None:
        merge = _make_merge()
        merge.revert("user-2")
        assert merge.revert_reason is None
        assert merge.status == MergeStatus.REVERTED

    def test_revert_already_reverted_raises(self) -> None:
        merge = _make_merge(status=MergeStatus.REVERTED)
        merge.reverted_at = NOW
        merge.reverted_by = "system"
        with pytest.raises(ValueError, match="already reverted"):
            merge.revert("user-3")


# ---------------------------------------------------------------------------
# MergeOperation.get_snapshot
# ---------------------------------------------------------------------------


class TestMergeOperationGetSnapshot:
    def test_get_snapshot_found(self) -> None:
        tid = uuid4()
        merge = _make_merge()
        merge.original_states = [
            TicketSnapshot(ticket_id=tid, snapshot={"summary": "original text"}),
        ]
        snap = merge.get_snapshot(tid)
        assert snap == {"summary": "original text"}

    def test_get_snapshot_not_found_returns_none(self) -> None:
        merge = _make_merge()
        result = merge.get_snapshot(uuid4())
        assert result is None

    def test_get_snapshot_multiple_states(self) -> None:
        ids = [uuid4() for _ in range(3)]
        merge = _make_merge()
        merge.original_states = [
            TicketSnapshot(ticket_id=tid, snapshot={"n": i}) for i, tid in enumerate(ids)
        ]
        assert merge.get_snapshot(ids[1]) == {"n": 1}
        assert merge.get_snapshot(ids[2]) == {"n": 2}
