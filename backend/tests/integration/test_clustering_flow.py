"""
Integration tests for clustering flow.

Tests end-to-end ticket ingestion to cluster creation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from deduptickets.main import app
from deduptickets.models.cluster import Cluster, ClusterStatus
from deduptickets.models.ticket import Ticket


@pytest.fixture
def mock_ticket_repository() -> AsyncMock:
    """Create mock ticket repository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.find_similar_tickets = AsyncMock(return_value=[])
    repo.assign_to_cluster = AsyncMock()
    repo.list_by_pk = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_cluster_repository() -> AsyncMock:
    """Create mock cluster repository."""
    repo = AsyncMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.list_pending = AsyncMock(return_value=[])
    repo.add_ticket = AsyncMock()
    return repo


class TestClusteringFlow:
    """Integration tests for clustering flow."""

    @pytest.mark.asyncio
    async def test_ingest_first_ticket_no_cluster(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """First ticket should not create a cluster."""
        ticket_id = uuid4()
        ticket_data = {
            "source_id": "TICKET-001",
            "source_system": "Zendesk",
            "title": "Payment failed for order 12345",
            "description": "Customer unable to complete payment.",
            "severity": "high",
            "product": "Payments",
            "region": "US",
        }

        created_ticket = Ticket(
            id=ticket_id,
            pk="US|2025-01",
            created_at=datetime.utcnow(),
            **ticket_data,
        )

        mock_ticket_repository.create.return_value = created_ticket
        mock_ticket_repository.find_similar_tickets.return_value = []

        with (
            patch(
                "deduptickets.routes.tickets.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.tickets.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/v1/tickets", json=ticket_data)

            assert response.status_code == 201
            data = response.json()
            assert data["source_id"] == ticket_data["source_id"]
            # No cluster should be created for single ticket
            mock_cluster_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_similar_ticket_creates_cluster(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Similar ticket should trigger cluster creation."""
        existing_ticket_id = uuid4()
        new_ticket_id = uuid4()
        cluster_id = uuid4()

        now = datetime.utcnow()

        existing_ticket = Ticket(
            id=existing_ticket_id,
            source_id="TICKET-001",
            source_system="Zendesk",
            title="Payment failed for order 12345",
            description="Customer unable to complete payment.",
            severity="high",
            product="Payments",
            region="US",
            created_at=now - timedelta(minutes=30),
            pk="US|2025-01",
        )

        new_ticket_data = {
            "source_id": "TICKET-002",
            "source_system": "Zendesk",
            "title": "Payment error for order 12346",
            "description": "Payment processing failed.",
            "severity": "high",
            "product": "Payments",
            "region": "US",
        }

        new_ticket = Ticket(
            id=new_ticket_id,
            pk="US|2025-01",
            created_at=now,
            **new_ticket_data,
        )

        created_cluster = Cluster(
            id=cluster_id,
            ticket_ids=[existing_ticket_id, new_ticket_id],
            ticket_count=2,
            confidence_score=0.85,
            status=ClusterStatus.PENDING,
            matching_fields=["product", "severity", "source_system"],
            created_at=now,
            pk="US|2025-01",
        )

        mock_ticket_repository.create.return_value = new_ticket
        mock_ticket_repository.find_similar_tickets.return_value = [existing_ticket]
        mock_cluster_repository.create.return_value = created_cluster

        with (
            patch(
                "deduptickets.routes.tickets.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.tickets.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/v1/tickets", json=new_ticket_data)

            assert response.status_code == 201
            # Cluster should be created
            mock_cluster_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_adds_to_existing_cluster(
        self,
        mock_ticket_repository: AsyncMock,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Should add ticket to existing cluster."""
        existing_ticket_id = uuid4()
        new_ticket_id = uuid4()
        cluster_id = uuid4()
        now = datetime.utcnow()

        existing_ticket = Ticket(
            id=existing_ticket_id,
            source_id="TICKET-001",
            source_system="Zendesk",
            title="Payment failed",
            description="Payment error",
            severity="high",
            product="Payments",
            region="US",
            cluster_id=cluster_id,  # Already in cluster
            created_at=now - timedelta(minutes=30),
            pk="US|2025-01",
        )

        existing_cluster = Cluster(
            id=cluster_id,
            ticket_ids=[existing_ticket_id],
            ticket_count=1,
            confidence_score=0.8,
            status=ClusterStatus.PENDING,
            matching_fields=["product"],
            created_at=now - timedelta(minutes=30),
            pk="US|2025-01",
        )

        new_ticket_data = {
            "source_id": "TICKET-003",
            "source_system": "Zendesk",
            "title": "Payment issue",
            "description": "Payment problem",
            "severity": "high",
            "product": "Payments",
            "region": "US",
        }

        new_ticket = Ticket(
            id=new_ticket_id,
            pk="US|2025-01",
            created_at=now,
            **new_ticket_data,
        )

        mock_ticket_repository.create.return_value = new_ticket
        mock_ticket_repository.find_similar_tickets.return_value = [existing_ticket]
        mock_cluster_repository.get_by_id.return_value = existing_cluster
        mock_cluster_repository.add_ticket.return_value = existing_cluster

        with (
            patch(
                "deduptickets.routes.tickets.get_ticket_repository",
                return_value=mock_ticket_repository,
            ),
            patch(
                "deduptickets.routes.tickets.get_cluster_repository",
                return_value=mock_cluster_repository,
            ),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post("/api/v1/tickets", json=new_ticket_data)

            assert response.status_code == 201
            # Should add to existing cluster, not create new
            mock_cluster_repository.add_ticket.assert_called_once()
            mock_cluster_repository.create.assert_not_called()


class TestClusterEndpoints:
    """Integration tests for cluster API endpoints."""

    @pytest.mark.asyncio
    async def test_list_clusters(
        self,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Should list pending clusters."""
        cluster = Cluster(
            id=uuid4(),
            ticket_ids=[uuid4(), uuid4()],
            ticket_count=2,
            confidence_score=0.85,
            status=ClusterStatus.PENDING,
            matching_fields=["product"],
            created_at=datetime.utcnow(),
            pk="US|2025-01",
        )

        mock_cluster_repository.list_pending.return_value = [cluster]

        with patch(
            "deduptickets.routes.clusters.get_cluster_repository",
            return_value=mock_cluster_repository,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/clusters?pk=US|2025-01")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["ticket_count"] == 2

    @pytest.mark.asyncio
    async def test_get_cluster_by_id(
        self,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Should get cluster by ID."""
        cluster_id = uuid4()
        cluster = Cluster(
            id=cluster_id,
            ticket_ids=[uuid4(), uuid4()],
            ticket_count=2,
            confidence_score=0.85,
            status=ClusterStatus.PENDING,
            matching_fields=["product"],
            created_at=datetime.utcnow(),
            pk="US|2025-01",
        )

        mock_cluster_repository.get_by_id.return_value = cluster

        with patch(
            "deduptickets.routes.clusters.get_cluster_repository",
            return_value=mock_cluster_repository,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/clusters/{cluster_id}?pk=US|2025-01")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(cluster_id)

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(
        self,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Should return 404 for non-existent cluster."""
        mock_cluster_repository.get_by_id.return_value = None

        with patch(
            "deduptickets.routes.clusters.get_cluster_repository",
            return_value=mock_cluster_repository,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/clusters/{uuid4()}?pk=US|2025-01")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_dismiss_cluster(
        self,
        mock_cluster_repository: AsyncMock,
    ) -> None:
        """Should dismiss cluster."""
        cluster_id = uuid4()
        cluster = Cluster(
            id=cluster_id,
            ticket_ids=[uuid4(), uuid4()],
            ticket_count=2,
            confidence_score=0.85,
            status=ClusterStatus.DISMISSED,
            matching_fields=["product"],
            created_at=datetime.utcnow(),
            dismissed_by="user@example.com",
            dismissal_reason="Not duplicates",
            pk="US|2025-01",
        )

        mock_cluster_repository.update_status.return_value = cluster

        with patch(
            "deduptickets.routes.clusters.get_cluster_repository",
            return_value=mock_cluster_repository,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/clusters/{cluster_id}/dismiss",
                    json={
                        "pk": "US|2025-01",
                        "dismissed_by": "user@example.com",
                        "reason": "Not duplicates",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "dismissed"
