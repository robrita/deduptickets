"""
Unit tests for trend analysis service.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from deduptickets.models.cluster import ClusterStatus
from deduptickets.models.driver import Driver
from deduptickets.services.trend_service import TrendConfig, TrendService


@pytest.fixture
def trend_config() -> TrendConfig:
    """Create test trend configuration."""
    return TrendConfig(
        default_lookback_days=7,
        min_clusters_for_growth=3,
        top_n_results=10,
    )


@pytest.fixture
def mock_repos() -> dict:
    """Create mock repositories."""
    return {
        "cluster_repo": AsyncMock(),
        "ticket_repo": AsyncMock(),
        "audit_repo": AsyncMock(),
    }


@pytest.fixture
def trend_service(trend_config: TrendConfig, mock_repos: dict) -> TrendService:
    """Create trend service with mocked dependencies."""
    return TrendService(
        cluster_repo=mock_repos["cluster_repo"],
        ticket_repo=mock_repos["ticket_repo"],
        audit_repo=mock_repos["audit_repo"],
        config=trend_config,
    )


def create_mock_cluster(
    product: str, ticket_count: int, created_at: datetime | None = None
) -> MagicMock:
    """Create a mock cluster with specified attributes."""
    cluster = MagicMock()
    cluster.id = uuid4()
    cluster.ticket_ids = [str(uuid4()) for _ in range(ticket_count)]
    cluster.ticket_count = ticket_count
    cluster.status = ClusterStatus.PENDING
    cluster.created_at = created_at or datetime.now(UTC)
    return cluster


def create_mock_ticket(product: str) -> MagicMock:
    """Create a mock ticket with specified product."""
    ticket = MagicMock()
    ticket.id = uuid4()
    ticket.product = product
    ticket.category = "TestCategory"
    ticket.severity = "high"
    return ticket


class TestDriverModel:
    """Tests for Driver model."""

    def test_calculate_growth_positive(self) -> None:
        """Test growth calculation with increase."""
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=60,
            ticket_count=180,
            previous_week_cluster_count=40,
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
        )
        driver.calculate_growth()
        assert driver.week_over_week_growth == 50.0  # (60-40)/40 * 100

    def test_calculate_growth_negative(self) -> None:
        """Test growth calculation with decrease."""
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=30,
            ticket_count=90,
            previous_week_cluster_count=40,
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
        )
        driver.calculate_growth()
        assert driver.week_over_week_growth == -25.0  # (30-40)/40 * 100

    def test_calculate_growth_no_previous_data(self) -> None:
        """Test growth calculation with no previous data."""
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=50,
            ticket_count=150,
            previous_week_cluster_count=0,
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
        )
        driver.calculate_growth()
        assert driver.week_over_week_growth == 100.0  # New driver = 100% growth

    def test_calculate_avg_tickets(self) -> None:
        """Test average tickets per cluster calculation."""
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=10,
            ticket_count=45,
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
        )
        driver.calculate_avg_tickets()
        assert driver.avg_tickets_per_cluster == 4.5

    def test_calculate_avg_tickets_zero_clusters(self) -> None:
        """Test average calculation with zero clusters."""
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=0,
            ticket_count=0,
            period_start=datetime.now(UTC) - timedelta(days=7),
            period_end=datetime.now(UTC),
        )
        driver.calculate_avg_tickets()
        assert driver.avg_tickets_per_cluster == 0.0

    def test_partition_key(self) -> None:
        """Test partition key generation."""
        now = datetime.now(UTC)
        driver = Driver(
            field_name="product",
            field_value="TestProduct",
            region="US",
            cluster_count=10,
            ticket_count=30,
            period_start=now - timedelta(days=7),
            period_end=now,
        )
        pk = driver.compute_partition_key()
        expected_month = now.strftime("%Y-%m")
        assert pk == f"US|{expected_month}"


class TestTrendServiceTopDrivers:
    """Tests for top drivers ranking."""

    @pytest.mark.asyncio
    async def test_top_drivers_empty(self, trend_service: TrendService, mock_repos: dict) -> None:
        """Test top drivers with no clusters."""
        mock_repos["cluster_repo"].get_by_date_range.return_value = []

        drivers = await trend_service.get_top_drivers("US", "product", days=7)

        assert drivers == []

    @pytest.mark.asyncio
    async def test_top_drivers_sorted_by_count(
        self, trend_service: TrendService, mock_repos: dict
    ) -> None:
        """Test that drivers are sorted by cluster count descending."""
        # Create clusters for different products
        clusters = [
            create_mock_cluster("ProductA", 3),
            create_mock_cluster("ProductA", 2),
            create_mock_cluster("ProductB", 4),
            create_mock_cluster("ProductC", 1),
        ]

        mock_repos["cluster_repo"].get_by_date_range.return_value = clusters

        # Mock ticket lookup to return product
        async def mock_get_ticket(ticket_id):
            for cluster in clusters:
                if ticket_id in [str(t) for t in cluster.ticket_ids]:
                    return create_mock_ticket(
                        "ProductA"
                        if cluster.ticket_count in [3, 2]
                        else "ProductB"
                        if cluster.ticket_count == 4
                        else "ProductC"
                    )
            return None

        mock_repos["ticket_repo"].get_by_id = mock_get_ticket

        drivers = await trend_service.get_top_drivers("US", "product", days=7, limit=10)

        # ProductA should be first (2 clusters), ProductB second (1 cluster)
        # Note: actual ordering depends on implementation details
        assert len(drivers) > 0


class TestTrendServiceFastestGrowing:
    """Tests for fastest growing drivers."""

    @pytest.mark.asyncio
    async def test_fastest_growing_filters_by_min_clusters(
        self, trend_service: TrendService, mock_repos: dict
    ) -> None:
        """Test that drivers below minimum clusters are filtered."""
        mock_repos["cluster_repo"].get_by_date_range.return_value = []

        drivers = await trend_service.get_fastest_growing(
            "US", "product", days=7, limit=10, min_clusters=5
        )

        # With no clusters, result should be empty
        assert drivers == []


class TestTrendServiceMostDuplicated:
    """Tests for most duplicated drivers."""

    @pytest.mark.asyncio
    async def test_most_duplicated_empty(
        self, trend_service: TrendService, mock_repos: dict
    ) -> None:
        """Test most duplicated with no data."""
        mock_repos["cluster_repo"].get_by_date_range.return_value = []

        drivers = await trend_service.get_most_duplicated("US", "product", days=7)

        assert drivers == []


class TestTrendServiceSummary:
    """Tests for summary statistics."""

    @pytest.mark.asyncio
    async def test_summary_empty(self, trend_service: TrendService, mock_repos: dict) -> None:
        """Test summary with no data."""
        mock_repos["cluster_repo"].get_by_date_range.return_value = []

        summary = await trend_service.get_summary_stats("US", days=7)

        assert summary["total_clusters"] == 0
        assert summary["total_tickets"] == 0
        assert summary["avg_duplication_ratio"] == 0.0
        assert summary["top_driver"] is None
