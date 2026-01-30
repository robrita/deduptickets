"""
Integration tests for merge revert flow.

Tests end-to-end merge → revert → verify restoration.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from deduptickets.main import app
from deduptickets.models.cluster import Cluster, ClusterStatus
from deduptickets.models.merge_operation import MergeOperation, MergeStatus
from deduptickets.models.ticket import Ticket


@pytest.fixture
def mock_ticket_repository() -> AsyncMock:
    """Create mock ticket repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_cluster_repository() -> AsyncMock:
    """Create mock cluster repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_merge_repository() -> AsyncMock:
    """Create mock merge repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update_status = AsyncMock()
    repo.list_by_pk = AsyncMock(return_value=[])
    repo.check_revert_conflicts = AsyncMock(return_value=[])
    repo.get_by_cluster_id = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_audit_repository() -> AsyncMock:
    """Create mock audit repository."""
    repo = AsyncMock()
    repo.log_action = AsyncMock()
    return repo


@pytest.fixture
def complete_merge_scenario() -> dict:
    """Create complete merge scenario with cluster, tickets, and merge."""
    cluster_id = uuid4()
    ticket1_id = uuid4()
    ticket2_id = uuid4()
    ticket3_id = uuid4()
    merge_id = uuid4()
    now = datetime.utcnow()

    cluster = Cluster(
        id=cluster_id,
        ticket_ids=[ticket1_id, ticket2_id, ticket3_id],
        ticket_count=3,
        confidence_score=0.85,
        status=ClusterStatus.MERGED,
        matching_fields=["product", "severity"],
        created_at=now - timedelta(hours=2),
        pk="US|2025-01",
    )

    tickets = [
        Ticket(
            id=ticket1_id,
            source_id="TICKET-001",
            source_system="Zendesk",
            title="Payment failed",
            description="Error during payment",
            severity="high",
            product="Payments",
            region="US",
            cluster_id=cluster_id,
            created_at=now - timedelta(hours=3),
            pk="US|2025-01",
        ),
        Ticket(
            id=ticket2_id,
            source_id="TICKET-002",
            source_system="Zendesk",
            title="Payment error",
            description="Unable to process payment",
            severity="high",
            product="Payments",
            region="US",
            cluster_id=cluster_id,
            merged_into_id=ticket1_id,  # Merged into canonical
            created_at=now - timedelta(hours=2),
            pk="US|2025-01",
        ),
        Ticket(
            id=ticket3_id,
            source_id="TICKET-003",
            source_system="Zendesk",
            title="Payment issue",
            description="Payment not working",
            severity="high",
            product="Payments",
            region="US",
            cluster_id=cluster_id,
            merged_into_id=ticket1_id,  # Merged into canonical
            created_at=now - timedelta(hours=1),
            pk="US|2025-01",
        ),
    ]

    merge = MergeOperation(
        id=merge_id,
        cluster_id=cluster_id,
        canonical_ticket_id=ticket1_id,
        merged_ticket_ids=[ticket2_id, ticket3_id],
        merged_by="user@example.com",
        merged_at=now - timedelta(hours=1),
        status=MergeStatus.COMPLETED,
        revert_deadline=now + timedelta(hours=23),
        original_states={
            str(ticket2_id): {
                "cluster_id": str(cluster_id),
                "merged_into_id": None,
                "updated_at": (now - timedelta(hours=2)).isoformat(),
            },
            str(ticket3_id): {
                "cluster_id": str(cluster_id),
                "merged_into_id": None,
                "updated_at": (now - timedelta(hours=1)).isoformat(),
            },
        },
        pk="US|2025-01",
    )

    return {
        "cluster": cluster,
        "tickets": tickets,
        "merge": merge,
        "cluster_id": cluster_id,
        "ticket_ids": [ticket1_id, ticket2_id, ticket3_id],
        "merge_id": merge_id,
    }


class TestMergeRevertIntegration:
    """End-to-end tests for merge → revert flow."""

    @pytest.mark.asyncio
    async def test_full_merge_revert_cycle(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_merge_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        complete_merge_scenario: dict,
    ) -> None:
        """Test complete merge → revert cycle restores original state."""
        scenario = complete_merge_scenario
        merge = scenario["merge"]
        cluster = scenario["cluster"]
        tickets = scenario["tickets"]

        # Set up mock responses
        mock_merge_repository.get_by_id.return_value = merge
        mock_merge_repository.check_revert_conflicts.return_value = []
        mock_merge_repository.update_status.return_value = MergeOperation(
            **{**merge.model_dump(), "status": MergeStatus.REVERTED}
        )

        async def get_ticket(tid, pk):
            return next((t for t in tickets if t.id == tid), None)

        mock_ticket_repository.get_by_id.side_effect = get_ticket
        mock_cluster_repository.update_status.return_value = Cluster(
            **{**cluster.model_dump(), "status": ClusterStatus.PENDING}
        )

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                # Execute revert
                response = await client.post(
                    f"/api/v1/merges/{merge.id}/revert",
                    params={"region": "US", "month": "2025-01"},
                    json={"reason": "Testing revert"},
                )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reverted"

            # Verify cluster was restored to pending
            mock_cluster_repository.update_status.assert_called_with(
                merge.cluster_id,
                ClusterStatus.PENDING,
                "US|2025-01",
            )

            # Verify audit was logged
            mock_audit_repository.log_action.assert_called_once()

    @pytest.mark.asyncio
    async def test_revert_respects_24_hour_window(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Test that reverts are blocked after 24-hour window."""
        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4(), uuid4()],
            merged_by="user@example.com",
            merged_at=now - timedelta(hours=30),  # 30 hours ago
            status=MergeStatus.COMPLETED,
            revert_deadline=now - timedelta(hours=6),  # Expired 6 hours ago
            pk="US|2025-01",
        )

        mock_merge_repository.get_by_id.return_value = merge

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/merges/{merge.id}/revert",
                    params={"region": "US", "month": "2025-01"},
                    json={},
                )

            assert response.status_code == 400
            assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_revert_conflict_detection(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Test that conflicts with subsequent merges are detected."""
        now = datetime.utcnow()
        original_merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            merged_at=now - timedelta(hours=2),
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=22),
            pk="US|2025-01",
        )

        conflicting_merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=original_merge.canonical_ticket_id,
            merged_ticket_ids=[uuid4()],
            merged_by="other@example.com",
            merged_at=now - timedelta(hours=1),
            status=MergeStatus.COMPLETED,
            pk="US|2025-01",
        )

        mock_merge_repository.get_by_id.return_value = original_merge
        mock_merge_repository.check_revert_conflicts.return_value = [conflicting_merge]

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/merges/{original_merge.id}/revert",
                    params={"region": "US", "month": "2025-01"},
                    json={},
                )

            assert response.status_code == 409
            assert "conflict" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_check_conflicts_endpoint(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Test the conflict check endpoint returns correct status."""
        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            merged_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=24),
            pk="US|2025-01",
        )

        mock_merge_repository.get_by_id.return_value = merge
        mock_merge_repository.check_revert_conflicts.return_value = []

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    f"/api/v1/merges/{merge.id}/conflicts",
                    params={"region": "US", "month": "2025-01"},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["has_conflicts"] is False
            assert data["conflicting_merge_ids"] == []

    @pytest.mark.asyncio
    async def test_double_revert_prevention(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Test that already reverted merges cannot be reverted again."""
        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            merged_at=now - timedelta(hours=2),
            status=MergeStatus.REVERTED,  # Already reverted
            reverted_by="admin@example.com",
            reverted_at=now - timedelta(hours=1),
            pk="US|2025-01",
        )

        mock_merge_repository.get_by_id.return_value = merge

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/merges/{merge.id}/revert",
                    params={"region": "US", "month": "2025-01"},
                    json={},
                )

            assert response.status_code == 400
            assert "already reverted" in response.json()["detail"].lower()


class TestMergeAuditTrail:
    """Tests for merge/revert audit trail."""

    @pytest.mark.asyncio
    async def test_revert_creates_audit_entry(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_merge_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        complete_merge_scenario: dict,
    ) -> None:
        """Test that revert creates proper audit entry."""
        scenario = complete_merge_scenario
        merge = scenario["merge"]
        tickets = scenario["tickets"]

        mock_merge_repository.get_by_id.return_value = merge
        mock_merge_repository.check_revert_conflicts.return_value = []
        mock_merge_repository.update_status.return_value = MergeOperation(
            **{**merge.model_dump(), "status": MergeStatus.REVERTED}
        )

        async def get_ticket(tid, pk):
            return next((t for t in tickets if t.id == tid), None)

        mock_ticket_repository.get_by_id.side_effect = get_ticket

        with (
            patch(
                "deduptickets.routes.merges.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_merge_repository",
                return_value=mock_merge_repository,
            ),
            patch(
                "deduptickets.routes.merges.get_audit_repository",
                return_value=mock_audit_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                await client.post(
                    f"/api/v1/merges/{merge.id}/revert",
                    params={"region": "US", "month": "2025-01"},
                    json={"reason": "Wrong merge decision"},
                )

            # Verify audit was called with correct action
            mock_audit_repository.log_action.assert_called_once()
            call_kwargs = mock_audit_repository.log_action.call_args.kwargs
            assert call_kwargs["entity_type"] == "merge"
            assert call_kwargs["entity_id"] == merge.id
            assert "REVERTED" in str(call_kwargs["action"])
