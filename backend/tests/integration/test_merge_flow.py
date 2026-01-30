"""
Integration tests for merge flow.

Tests end-to-end cluster merge and revert operations.
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
def sample_cluster_with_tickets() -> tuple[Cluster, list[Ticket]]:
    """Create sample cluster with tickets."""
    ticket1_id = uuid4()
    ticket2_id = uuid4()
    ticket3_id = uuid4()
    cluster_id = uuid4()
    now = datetime.utcnow()

    cluster = Cluster(
        id=cluster_id,
        ticket_ids=[ticket1_id, ticket2_id, ticket3_id],
        ticket_count=3,
        confidence_score=0.85,
        status=ClusterStatus.PENDING,
        matching_fields=["product", "severity"],
        created_at=now,
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
            created_at=now - timedelta(hours=2),
            pk="US|2025-01",
        ),
        Ticket(
            id=ticket2_id,
            source_id="TICKET-002",
            source_system="Zendesk",
            title="Payment error",
            description="Unable to process",
            severity="high",
            product="Payments",
            region="US",
            cluster_id=cluster_id,
            created_at=now - timedelta(hours=1),
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
            created_at=now,
            pk="US|2025-01",
        ),
    ]

    return cluster, tickets


class TestMergeFlow:
    """Integration tests for merge flow."""

    @pytest.mark.asyncio
    async def test_merge_cluster_success(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_merge_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        sample_cluster_with_tickets: tuple[Cluster, list[Ticket]],
    ) -> None:
        """Should successfully merge cluster."""
        cluster, tickets = sample_cluster_with_tickets
        canonical_id = tickets[0].id
        now = datetime.utcnow()

        merge = MergeOperation(
            id=uuid4(),
            cluster_id=cluster.id,
            canonical_ticket_id=canonical_id,
            merged_ticket_ids=[t.id for t in tickets[1:]],
            merged_by="user@example.com",
            merged_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=24),
            pk="US|2025-01",
        )

        mock_cluster_repository.get_by_id.return_value = cluster

        async def get_ticket(tid, pk):
            return next((t for t in tickets if t.id == tid), None)

        mock_ticket_repository.get_by_id.side_effect = get_ticket
        mock_merge_repository.create.return_value = merge
        mock_cluster_repository.update_status.return_value = Cluster(
            **{**cluster.model_dump(), "status": ClusterStatus.MERGED}
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
                response = await client.post(
                    "/api/v1/merges",
                    json={
                        "cluster_id": str(cluster.id),
                        "canonical_ticket_id": str(canonical_id),
                        "pk": "US|2025-01",
                        "merged_by": "user@example.com",
                    },
                )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "completed"
            assert data["canonical_ticket_id"] == str(canonical_id)

    @pytest.mark.asyncio
    async def test_merge_cluster_not_found(
        self,
        mock_cluster_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_merge_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Should return 404 when cluster not found."""
        mock_cluster_repository.get_by_id.return_value = None

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
                    "/api/v1/merges",
                    json={
                        "cluster_id": str(uuid4()),
                        "canonical_ticket_id": str(uuid4()),
                        "pk": "US|2025-01",
                        "merged_by": "user@example.com",
                    },
                )

            assert response.status_code == 404


class TestRevertFlow:
    """Integration tests for revert flow."""

    @pytest.mark.asyncio
    async def test_revert_merge_success(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_merge_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
        sample_cluster_with_tickets: tuple[Cluster, list[Ticket]],
    ) -> None:
        """Should successfully revert merge."""
        cluster, tickets = sample_cluster_with_tickets
        now = datetime.utcnow()

        merge = MergeOperation(
            id=uuid4(),
            cluster_id=cluster.id,
            canonical_ticket_id=tickets[0].id,
            merged_ticket_ids=[t.id for t in tickets[1:]],
            merged_by="user@example.com",
            merged_at=now - timedelta(hours=1),
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=23),
            original_states={
                str(tickets[1].id): {"cluster_id": str(cluster.id)},
                str(tickets[2].id): {"cluster_id": str(cluster.id)},
            },
            pk="US|2025-01",
        )

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
                response = await client.post(
                    f"/api/v1/merges/{merge.id}/revert",
                    json={
                        "pk": "US|2025-01",
                        "reverted_by": "admin@example.com",
                        "reason": "Wrong merge",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reverted"

    @pytest.mark.asyncio
    async def test_revert_expired_window(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Should reject revert after window expires."""
        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            merged_at=now - timedelta(days=2),
            status=MergeStatus.COMPLETED,
            revert_deadline=now - timedelta(days=1),  # Expired
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
                    json={
                        "pk": "US|2025-01",
                        "reverted_by": "admin@example.com",
                    },
                )

            # Should return 400 for expired revert window
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_check_revert_eligibility(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Should check revert eligibility."""
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
                response = await client.get(f"/api/v1/merges/{merge.id}/revert-check?pk=US|2025-01")

            assert response.status_code == 200
            data = response.json()
            assert data["eligible"] is True
            assert data["has_conflicts"] is False


class TestMergeListEndpoints:
    """Integration tests for merge list endpoints."""

    @pytest.mark.asyncio
    async def test_list_merges(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Should list merge operations."""
        now = datetime.utcnow()
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4(), uuid4()],
            merged_by="user@example.com",
            merged_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=24),
            pk="US|2025-01",
        )

        mock_merge_repository.list_by_pk.return_value = [merge]

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
                response = await client.get("/api/v1/merges?pk=US|2025-01")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_merge_by_id(
        self,
        mock_merge_repository: AsyncMock,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
        mock_audit_repository: AsyncMock,
    ) -> None:
        """Should get merge by ID."""
        now = datetime.utcnow()
        merge_id = uuid4()
        merge = MergeOperation(
            id=merge_id,
            cluster_id=uuid4(),
            canonical_ticket_id=uuid4(),
            merged_ticket_ids=[uuid4()],
            merged_by="user@example.com",
            merged_at=now,
            status=MergeStatus.COMPLETED,
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
                response = await client.get(f"/api/v1/merges/{merge_id}?pk=US|2025-01")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(merge_id)
