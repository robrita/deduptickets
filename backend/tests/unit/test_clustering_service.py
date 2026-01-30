"""
Unit tests for ClusteringService.

Tests clustering logic, similarity scoring, and cluster assignment.
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
)
from deduptickets.models.ticket import Ticket
from deduptickets.services.clustering_service import (
    ClusteringConfig,
    ClusteringService,
    calculate_confidence_score,
    calculate_time_proximity,
)


@pytest.fixture
def mock_ticket_repo() -> AsyncMock:
    """Create mock ticket repository."""
    repo = AsyncMock()
    repo.find_similar_tickets = AsyncMock(return_value=[])
    repo.assign_to_cluster = AsyncMock()
    repo.remove_from_cluster = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_cluster_repo() -> AsyncMock:
    """Create mock cluster repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.add_ticket = AsyncMock()
    repo.remove_ticket = AsyncMock()
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def clustering_config() -> ClusteringConfig:
    """Create test clustering configuration."""
    return ClusteringConfig(
        similarity_threshold=0.7,
        time_window_hours=1,
        min_cluster_size=2,
        exact_match_fields=["category", "severity", "channel"],
    )


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create sample ticket for testing."""
    now = datetime.utcnow()
    return Ticket(
        id=uuid4(),
        pk="US|2025-01",
        ticket_number="TICKET-001",
        created_at=now,
        updated_at=now,
        channel="InApp",
        customer_id="CUST-001",
        category="Payments",
        subcategory="Payment Failed",
        summary="Payment failed for order 12345",
        description="Customer unable to complete payment. Error code: PAY-500.",
        severity="high",
        region="US",
    )


class TestCalculateConfidenceScore:
    """Tests for confidence score calculation."""

    def test_perfect_score(self) -> None:
        """Should return 1.0 for perfect matches."""
        score = calculate_confidence_score(
            exact_field_matches=3,
            total_exact_fields=3,
            text_similarity=1.0,
            time_proximity=1.0,
        )
        assert score == pytest.approx(1.0)

    def test_zero_score(self) -> None:
        """Should return 0.0 for no matches."""
        score = calculate_confidence_score(
            exact_field_matches=0,
            total_exact_fields=3,
            text_similarity=0.0,
            time_proximity=0.0,
        )
        assert score == pytest.approx(0.0)

    def test_partial_score(self) -> None:
        """Should calculate correct weighted score."""
        score = calculate_confidence_score(
            exact_field_matches=2,  # 2/3 = 0.667
            total_exact_fields=3,
            text_similarity=0.8,
            time_proximity=0.5,
        )
        # Expected: (0.667 * 0.4) + (0.8 * 0.4) + (0.5 * 0.2) = 0.687
        expected = (2 / 3 * 0.4) + (0.8 * 0.4) + (0.5 * 0.2)
        assert score == pytest.approx(expected)

    def test_no_exact_fields(self) -> None:
        """Should handle zero total exact fields."""
        score = calculate_confidence_score(
            exact_field_matches=0,
            total_exact_fields=0,  # No fields to check
            text_similarity=0.9,
            time_proximity=0.8,
        )
        # Expected: (0 * 0.4) + (0.9 * 0.4) + (0.8 * 0.2) = 0.52
        expected = (0.9 * 0.4) + (0.8 * 0.2)
        assert score == pytest.approx(expected)


class TestCalculateTimeProximity:
    """Tests for time proximity calculation."""

    def test_identical_times(self) -> None:
        """Should return 1.0 for identical times."""
        now = datetime.utcnow()
        proximity = calculate_time_proximity(now, now, window_hours=1)
        assert proximity == pytest.approx(1.0)

    def test_edge_of_window(self) -> None:
        """Should return 0.0 at edge of window."""
        now = datetime.utcnow()
        one_hour_later = now + timedelta(hours=1)
        proximity = calculate_time_proximity(now, one_hour_later, window_hours=1)
        assert proximity == pytest.approx(0.0)

    def test_beyond_window(self) -> None:
        """Should return 0.0 beyond window."""
        now = datetime.utcnow()
        two_hours_later = now + timedelta(hours=2)
        proximity = calculate_time_proximity(now, two_hours_later, window_hours=1)
        assert proximity == pytest.approx(0.0)

    def test_half_window(self) -> None:
        """Should return 0.5 at half of window."""
        now = datetime.utcnow()
        half_hour_later = now + timedelta(minutes=30)
        proximity = calculate_time_proximity(now, half_hour_later, window_hours=1)
        assert proximity == pytest.approx(0.5)

    def test_symmetric(self) -> None:
        """Should be symmetric (order doesn't matter)."""
        now = datetime.utcnow()
        later = now + timedelta(minutes=30)
        assert calculate_time_proximity(now, later, 1) == calculate_time_proximity(later, now, 1)


class TestClusteringConfig:
    """Tests for ClusteringConfig."""

    def test_default_values(self) -> None:
        """Should have sensible defaults."""
        config = ClusteringConfig()
        assert config.similarity_threshold == 0.7
        assert config.time_window_hours == 1
        assert config.min_cluster_size == 2

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        config = ClusteringConfig(
            similarity_threshold=0.8,
            time_window_hours=2,
            min_cluster_size=3,
            exact_match_fields=["category"],
        )
        assert config.similarity_threshold == 0.8
        assert config.time_window_hours == 2
        assert config.min_cluster_size == 3
        assert config.exact_match_fields == ["category"]


class TestClusteringService:
    """Tests for ClusteringService."""

    @pytest.mark.asyncio
    async def test_find_or_create_cluster_no_candidates(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        clustering_config: ClusteringConfig,
        sample_ticket: Ticket,
    ) -> None:
        """Should return None when no candidates found."""
        service = ClusteringService(
            mock_ticket_repo,
            mock_cluster_repo,
            clustering_config,
        )

        mock_ticket_repo.find_similar_tickets.return_value = []

        result = await service.find_or_create_cluster(sample_ticket, "US|2025-01")

        assert result is None
        mock_ticket_repo.find_similar_tickets.assert_called_once()
        mock_cluster_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_or_create_cluster_creates_new(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        clustering_config: ClusteringConfig,
        sample_ticket: Ticket,
    ) -> None:
        """Should create new cluster when good match found."""
        service = ClusteringService(
            mock_ticket_repo,
            mock_cluster_repo,
            clustering_config,
        )

        # Create a similar candidate ticket
        now = datetime.utcnow()
        candidate = Ticket(
            id=uuid4(),
            pk="US|2025-01",
            ticket_number="TICKET-002",
            created_at=now - timedelta(minutes=30),
            updated_at=now,
            channel=sample_ticket.channel,
            customer_id="CUST-002",
            category=sample_ticket.category,
            summary="Payment failed for order 12346",
            description="Payment error occurred. Error: PAY-500.",
            severity=sample_ticket.severity,
            region="US",
        )

        mock_ticket_repo.find_similar_tickets.return_value = [candidate]
        mock_cluster_repo.create.return_value = Cluster(
            id=uuid4(),
            pk="US|2025-01",
            members=[
                ClusterMember(ticket_id=sample_ticket.id, ticket_number="TICKET-001"),
                ClusterMember(ticket_id=candidate.id, ticket_number="TICKET-002"),
            ],
            ticket_count=2,
            confidence=ConfidenceLevel.HIGH,
            summary="Payment failures",
            status=ClusterStatus.PENDING,
        )

        result = await service.find_or_create_cluster(sample_ticket, "US|2025-01")

        assert result is not None
        assert result.ticket_count == 2
        mock_cluster_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_or_create_cluster_adds_to_existing(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        clustering_config: ClusteringConfig,
        sample_ticket: Ticket,
    ) -> None:
        """Should add to existing cluster when candidate is already clustered."""
        service = ClusteringService(
            mock_ticket_repo,
            mock_cluster_repo,
            clustering_config,
        )

        existing_cluster_id = uuid4()

        # Create a candidate that's already in a cluster with matching fields
        now = datetime.utcnow()
        candidate = Ticket(
            id=uuid4(),
            pk="US|2025-01",
            ticket_number="TICKET-002",
            created_at=now - timedelta(minutes=30),
            updated_at=now,
            channel=sample_ticket.channel,
            customer_id="CUST-002",
            category=sample_ticket.category,
            # Use identical summary/description to ensure high similarity
            summary=sample_ticket.summary,
            description=sample_ticket.description,
            severity=sample_ticket.severity,
            region="US",
            cluster_id=existing_cluster_id,
        )

        existing_cluster = Cluster(
            id=existing_cluster_id,
            pk="US|2025-01",
            members=[
                ClusterMember(ticket_id=candidate.id, ticket_number="TICKET-002"),
                ClusterMember(ticket_id=uuid4(), ticket_number="TICKET-003"),
            ],
            ticket_count=2,
            confidence=ConfidenceLevel.MEDIUM,
            summary="Payment issues",
            status=ClusterStatus.PENDING,
        )

        mock_ticket_repo.find_similar_tickets.return_value = [candidate]
        mock_cluster_repo.get_by_id.return_value = existing_cluster
        mock_cluster_repo.add_ticket.return_value = existing_cluster

        result = await service.find_or_create_cluster(sample_ticket, "US|2025-01")

        assert result is not None
        mock_cluster_repo.add_ticket.assert_called_once()
        mock_cluster_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_dismiss_cluster(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        clustering_config: ClusteringConfig,
    ) -> None:
        """Should dismiss cluster with reason."""
        service = ClusteringService(
            mock_ticket_repo,
            mock_cluster_repo,
            clustering_config,
        )

        cluster_id = uuid4()
        ticket1, ticket2 = uuid4(), uuid4()
        mock_cluster_repo.update_status.return_value = Cluster(
            id=cluster_id,
            pk="US|2025-01",
            members=[
                ClusterMember(ticket_id=ticket1, ticket_number="T-001"),
                ClusterMember(ticket_id=ticket2, ticket_number="T-002"),
            ],
            ticket_count=2,
            confidence=ConfidenceLevel.MEDIUM,
            summary="Test cluster",
            status=ClusterStatus.DISMISSED,
        )

        result = await service.dismiss_cluster(
            cluster_id,
            "US|2025-01",
            dismissed_by="user@example.com",
            reason="Not duplicates",
        )

        assert result is not None
        assert result.status == ClusterStatus.DISMISSED
        mock_cluster_repo.update_status.assert_called_once_with(
            cluster_id,
            ClusterStatus.DISMISSED,
            "US|2025-01",
            dismissed_by="user@example.com",
            dismissal_reason="Not duplicates",
        )

    @pytest.mark.asyncio
    async def test_remove_ticket_auto_dismisses_small_cluster(
        self,
        mock_ticket_repo: AsyncMock,
        mock_cluster_repo: AsyncMock,
        clustering_config: ClusteringConfig,
    ) -> None:
        """Should auto-dismiss cluster when it becomes too small."""
        service = ClusteringService(
            mock_ticket_repo,
            mock_cluster_repo,
            clustering_config,
        )

        cluster_id = uuid4()
        ticket_id = uuid4()
        remaining_ticket = uuid4()

        # After removal, cluster has only 1 ticket - use a mock for this edge case
        # since Cluster model requires ticket_count >= 2
        small_cluster = AsyncMock()
        small_cluster.ticket_count = 1
        small_cluster.status = ClusterStatus.PENDING
        mock_cluster_repo.remove_ticket.return_value = small_cluster

        dismissed_cluster = Cluster(
            id=cluster_id,
            pk="US|2025-01",
            members=[
                ClusterMember(ticket_id=remaining_ticket, ticket_number="T-001"),
                ClusterMember(ticket_id=uuid4(), ticket_number="T-002"),
            ],
            ticket_count=2,
            confidence=ConfidenceLevel.MEDIUM,
            summary="Cluster became too small",
            status=ClusterStatus.DISMISSED,
        )
        mock_cluster_repo.update_status.return_value = dismissed_cluster

        result = await service.remove_ticket_from_cluster(cluster_id, ticket_id, "US|2025-01")

        assert result is not None
        assert result.status == ClusterStatus.DISMISSED
        mock_cluster_repo.update_status.assert_called_once()
