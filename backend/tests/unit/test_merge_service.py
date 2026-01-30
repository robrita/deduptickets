"""
Unit tests for MergeService.

Tests merge operations, revert logic, and conflict detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from deduptickets.models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
    ConfidenceLevel,
    MatchingSignals,
)
from deduptickets.models.merge_operation import (
    MergeOperation,
    MergeStatus,
    TicketSnapshot,
)
from deduptickets.models.ticket import Ticket
from deduptickets.services.merge_service import (
    MergeAlreadyRevertedError,
    MergeConflictError,
    MergeNotFoundError,
    MergeService,
    RevertWindowExpiredError,
)


@pytest.fixture
def mock_ticket_repo() -> AsyncMock:
    """Create mock ticket repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_cluster_repo() -> AsyncMock:
    """Create mock cluster repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_merge_repo() -> AsyncMock:
    """Create mock merge repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update_status = AsyncMock()
    repo.check_revert_conflicts = AsyncMock(return_value=[])
    repo.get_by_cluster_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_audit_repo() -> AsyncMock:
    """Create mock audit repository."""
    repo = AsyncMock()
    repo.log_action = AsyncMock()
    return repo


@pytest.fixture
def sample_cluster() -> Cluster:
    """Create sample cluster for testing."""
    ticket1_id = uuid4()
    ticket2_id = uuid4()
    ticket3_id = uuid4()
    now = datetime.utcnow()

    return Cluster(
        id=uuid4(),
        members=[
            ClusterMember(ticket_id=ticket1_id, ticket_number="TKT-001", added_at=now),
            ClusterMember(ticket_id=ticket2_id, ticket_number="TKT-002", added_at=now),
            ClusterMember(ticket_id=ticket3_id, ticket_number="TKT-003", added_at=now),
        ],
        ticket_count=3,
        confidence=ConfidenceLevel.HIGH,
        summary="Duplicate payment failure tickets",
        status=ClusterStatus.PENDING,
        matching_signals=MatchingSignals(),
        created_at=now,
        pk="US|2025-01",
    )


@pytest.fixture
def sample_tickets(sample_cluster: Cluster) -> list[Ticket]:
    """Create sample tickets for testing."""
    ticket_ids = sample_cluster.ticket_ids
    now = datetime.utcnow()

    return [
        Ticket(
            id=ticket_ids[0],
            ticket_number="TKT-001",
            summary="Payment failed",
            description="Error during payment",
            category="Payments",
            channel="chat",
            customer_id="CUST-001",
            region="US",
            cluster_id=sample_cluster.id,
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
            pk="US|2025-01",
        ),
        Ticket(
            id=ticket_ids[1],
            ticket_number="TKT-002",
            summary="Payment error",
            description="Unable to process payment",
            category="Payments",
            channel="chat",
            customer_id="CUST-002",
            region="US",
            cluster_id=sample_cluster.id,
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1),
            pk="US|2025-01",
        ),
        Ticket(
            id=ticket_ids[2],
            ticket_number="TKT-003",
            summary="Payment issue",
            description="Payment not working",
            category="Payments",
            channel="chat",
            customer_id="CUST-003",
            region="US",
            cluster_id=sample_cluster.id,
            created_at=now,
            updated_at=now,
            pk="US|2025-01",
        ),
    ]


class TestMergeCluster:
    """Tests for merge_cluster method."""

    @pytest.mark.asyncio
    async def test_merge_success(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
        sample_cluster: Cluster,
        sample_tickets: list[Ticket],
    ) -> None:
        """Should successfully merge cluster."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        canonical_id = sample_tickets[0].id
        mock_cluster_repo.get_by_id.return_value = sample_cluster

        # Set up ticket retrieval for state capture
        async def get_ticket(tid: uuid4, pk: str) -> Ticket | None:
            return next((t for t in sample_tickets if t.id == tid), None)

        mock_ticket_repo.get_by_id.side_effect = get_ticket
        mock_merge_repo.create.return_value = MergeOperation(
            id=uuid4(),
            cluster_id=sample_cluster.id,
            primary_ticket_id=canonical_id,
            secondary_ticket_ids=[t.id for t in sample_tickets[1:]],
            merged_by="user@example.com",
            performed_at=datetime.utcnow(),
            status=MergeStatus.COMPLETED,
            revert_deadline=datetime.utcnow() + timedelta(hours=24),
            pk="US|2025-01",
        )

        result = await service.merge_cluster(
            sample_cluster.id,
            canonical_id,
            "US|2025-01",
            merged_by="user@example.com",
        )

        assert result.status == MergeStatus.COMPLETED
        assert result.primary_ticket_id == canonical_id
        assert len(result.secondary_ticket_ids) == 2
        mock_cluster_repo.update_status.assert_called_once()
        mock_audit_repo.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_merge_cluster_not_found(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should raise error when cluster not found."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        mock_cluster_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="not found"):
            await service.merge_cluster(
                uuid4(),
                uuid4(),
                "US|2025-01",
                merged_by="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_merge_cluster_not_pending(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
        sample_cluster: Cluster,
    ) -> None:
        """Should raise error when cluster is not pending."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        sample_cluster.status = ClusterStatus.MERGED
        mock_cluster_repo.get_by_id.return_value = sample_cluster

        with pytest.raises(ValueError, match="status"):
            await service.merge_cluster(
                sample_cluster.id,
                sample_cluster.ticket_ids[0],
                "US|2025-01",
                merged_by="user@example.com",
            )

    @pytest.mark.asyncio
    async def test_merge_canonical_not_in_cluster(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
        sample_cluster: Cluster,
    ) -> None:
        """Should raise error when canonical ticket not in cluster."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        mock_cluster_repo.get_by_id.return_value = sample_cluster

        with pytest.raises(ValueError, match="not in the cluster"):
            await service.merge_cluster(
                sample_cluster.id,
                uuid4(),  # Not in cluster
                "US|2025-01",
                merged_by="user@example.com",
            )


class TestRevertMerge:
    """Tests for revert_merge method."""

    @pytest.mark.asyncio
    async def test_revert_success(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
        sample_cluster: Cluster,
        sample_tickets: list[Ticket],
    ) -> None:
        """Should successfully revert merge."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=sample_cluster.id,
            primary_ticket_id=sample_tickets[0].id,
            secondary_ticket_ids=[t.id for t in sample_tickets[1:]],
            merged_by="user@example.com",
            performed_at=now - timedelta(hours=1),
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=23),
            original_states=[
                TicketSnapshot(
                    ticket_id=sample_tickets[1].id,
                    snapshot={"cluster_id": str(sample_cluster.id)},
                ),
                TicketSnapshot(
                    ticket_id=sample_tickets[2].id,
                    snapshot={"cluster_id": str(sample_cluster.id)},
                ),
            ],
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge
        mock_merge_repo.check_revert_conflicts.return_value = []
        mock_merge_repo.update_status.return_value = MergeOperation(
            **{**merge.model_dump(), "status": MergeStatus.REVERTED}
        )

        async def get_ticket(tid: uuid4, pk: str) -> Ticket | None:
            return next((t for t in sample_tickets if t.id == tid), None)

        mock_ticket_repo.get_by_id.side_effect = get_ticket

        result = await service.revert_merge(
            merge.id,
            "US|2025-01",
            reverted_by="admin@example.com",
            reason="Wrong merge",
        )

        assert result.status == MergeStatus.REVERTED
        mock_cluster_repo.update_status.assert_called_once()
        mock_audit_repo.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_revert_not_found(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should raise error when merge not found."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        mock_merge_repo.get_by_id.return_value = None

        with pytest.raises(MergeNotFoundError):
            await service.revert_merge(
                uuid4(),
                "US|2025-01",
                reverted_by="admin@example.com",
            )

    @pytest.mark.asyncio
    async def test_revert_already_reverted(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should raise error when already reverted."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=uuid4(),
            secondary_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            performed_at=datetime.utcnow(),
            status=MergeStatus.REVERTED,  # Already reverted
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge

        with pytest.raises(MergeAlreadyRevertedError):
            await service.revert_merge(
                merge.id,
                "US|2025-01",
                reverted_by="admin@example.com",
            )

    @pytest.mark.asyncio
    async def test_revert_window_expired(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should raise error when revert window expired."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=uuid4(),
            secondary_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            performed_at=now - timedelta(days=2),
            status=MergeStatus.COMPLETED,
            revert_deadline=now - timedelta(days=1),  # Expired
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge

        with pytest.raises(RevertWindowExpiredError):
            await service.revert_merge(
                merge.id,
                "US|2025-01",
                reverted_by="admin@example.com",
            )

    @pytest.mark.asyncio
    async def test_revert_with_conflicts_raises(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should raise error when conflicts detected."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=uuid4(),
            secondary_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            performed_at=now - timedelta(hours=1),
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=23),
            pk="US|2025-01",
        )

        conflicting_merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=merge.primary_ticket_id,
            secondary_ticket_ids=[uuid4()],
            performed_by="other@example.com",
            performed_at=now,
            status=MergeStatus.COMPLETED,
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge
        mock_merge_repo.check_revert_conflicts.return_value = [conflicting_merge]

        with pytest.raises(MergeConflictError) as exc_info:
            await service.revert_merge(
                merge.id,
                "US|2025-01",
                reverted_by="admin@example.com",
            )

        assert len(exc_info.value.conflicts) > 0

    @pytest.mark.asyncio
    async def test_revert_with_conflicts_force(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
        sample_tickets: list[Ticket],
    ) -> None:
        """Should allow force revert with conflicts."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=sample_tickets[0].id,
            secondary_ticket_ids=[t.id for t in sample_tickets[1:]],
            merged_by="user@example.com",
            performed_at=now - timedelta(hours=1),
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=23),
            original_states=[],
            pk="US|2025-01",
        )

        conflicting_merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=merge.primary_ticket_id,
            secondary_ticket_ids=[uuid4()],
            performed_by="other@example.com",
            performed_at=now,
            status=MergeStatus.COMPLETED,
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge
        mock_merge_repo.check_revert_conflicts.return_value = [conflicting_merge]
        mock_merge_repo.update_status.return_value = MergeOperation(
            **{**merge.model_dump(), "status": MergeStatus.REVERTED}
        )

        async def get_ticket(tid: uuid4, pk: str) -> Ticket | None:
            return next((t for t in sample_tickets if t.id == tid), None)

        mock_ticket_repo.get_by_id.side_effect = get_ticket

        result = await service.revert_merge(
            merge.id,
            "US|2025-01",
            reverted_by="admin@example.com",
            force=True,  # Force despite conflicts
        )

        assert result.status == MergeStatus.REVERTED


class TestCheckRevertEligible:
    """Tests for check_revert_eligible method."""

    @pytest.mark.asyncio
    async def test_eligible_no_conflicts(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should return eligible when no issues."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=uuid4(),
            secondary_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            performed_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=24),
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge
        mock_merge_repo.check_revert_conflicts.return_value = []

        result = await service.check_revert_eligible(merge.id, "US|2025-01")

        assert result["eligible"] is True
        assert result["has_conflicts"] is False

    @pytest.mark.asyncio
    async def test_eligible_with_conflicts(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        mock_merge_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        """Should return eligible with conflicts warning."""
        service = MergeService(
            mock_ticket_repo,
            mock_cluster_repo,
            mock_merge_repo,
            mock_audit_repo,
        )

        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            primary_ticket_id=uuid4(),
            secondary_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            performed_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=24),
            pk="US|2025-01",
        )

        mock_merge_repo.get_by_id.return_value = merge
        mock_merge_repo.check_revert_conflicts.return_value = [
            MergeOperation(
                id=uuid4(),
                cluster_id=uuid4(),
                primary_ticket_id=merge.primary_ticket_id,
                secondary_ticket_ids=[],
                performed_by="other",
                performed_at=now,
                status=MergeStatus.COMPLETED,
                pk="US|2025-01",
            )
        ]

        result = await service.check_revert_eligible(merge.id, "US|2025-01")

        assert result["eligible"] is True
        assert result["has_conflicts"] is True
        assert len(result["conflicts"]) > 0
