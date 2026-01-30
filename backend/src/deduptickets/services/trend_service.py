"""
Trend analysis service.

Provides aggregation methods for identifying top drivers,
fastest growing issues, and most duplicated ticket patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from deduptickets.models.driver import Driver

if TYPE_CHECKING:
    from deduptickets.repositories.audit import AuditRepository
    from deduptickets.repositories.cluster import ClusterRepository
    from deduptickets.repositories.ticket import TicketRepository


@dataclass
class TrendConfig:
    """Configuration for trend analysis."""

    default_lookback_days: int = 7
    min_clusters_for_growth: int = 3  # Minimum clusters to include in growth ranking
    top_n_results: int = 10  # Default number of results for top-N queries


class TrendService:
    """
    Service for analyzing ticket trends and identifying drivers.

    A "driver" is a recurring theme (product, category, etc.) that groups
    related clusters for trend analysis.
    """

    def __init__(
        self,
        cluster_repo: ClusterRepository,
        ticket_repo: TicketRepository,
        audit_repo: AuditRepository,
        config: TrendConfig | None = None,
    ) -> None:
        """Initialize trend service with repositories."""
        self._cluster_repo = cluster_repo
        self._ticket_repo = ticket_repo
        self._audit_repo = audit_repo
        self._config = config or TrendConfig()

    async def get_top_drivers(
        self,
        region: str,
        field_name: str = "product",
        days: int = 7,
        limit: int = 10,
    ) -> list[Driver]:
        """
        Get top drivers ranked by cluster count.

        Args:
            region: Region to analyze
            field_name: Field to group by (product, category, etc.)
            days: Lookback period in days
            limit: Maximum drivers to return

        Returns:
            List of Driver objects ranked by cluster_count descending
        """
        now = datetime.now(UTC)
        period_start = now - timedelta(days=days)
        period_end = now
        prev_period_start = period_start - timedelta(days=days)

        # Get current period aggregation
        current_aggregation = await self._aggregate_by_field(
            region, field_name, period_start, period_end
        )

        # Get previous period for growth calculation
        prev_aggregation = await self._aggregate_by_field(
            region, field_name, prev_period_start, period_start
        )

        drivers = []
        for field_value, counts in current_aggregation.items():
            prev_counts = prev_aggregation.get(field_value, {"clusters": 0, "tickets": 0})

            driver = Driver(
                field_name=field_name,
                field_value=field_value,
                region=region,
                cluster_count=counts["clusters"],
                ticket_count=counts["tickets"],
                previous_week_cluster_count=prev_counts["clusters"],
                period_start=period_start,
                period_end=period_end,
            )
            driver.calculate_growth()
            driver.calculate_avg_tickets()
            drivers.append(driver)

        # Sort by cluster count descending
        drivers.sort(key=lambda d: d.cluster_count, reverse=True)
        return drivers[:limit]

    async def get_fastest_growing(
        self,
        region: str,
        field_name: str = "product",
        days: int = 7,
        limit: int = 10,
        min_clusters: int | None = None,
    ) -> list[Driver]:
        """
        Get fastest growing drivers by week-over-week growth percentage.

        Args:
            region: Region to analyze
            field_name: Field to group by
            days: Lookback period in days
            limit: Maximum drivers to return
            min_clusters: Minimum clusters to include (filters noise)

        Returns:
            List of Driver objects ranked by week_over_week_growth descending
        """
        min_clusters = min_clusters or self._config.min_clusters_for_growth

        # Get all drivers first
        all_drivers = await self.get_top_drivers(region, field_name, days, limit=100)

        # Filter by minimum clusters and sort by growth
        filtered = [d for d in all_drivers if d.cluster_count >= min_clusters]
        filtered.sort(key=lambda d: d.week_over_week_growth, reverse=True)

        return filtered[:limit]

    async def get_most_duplicated(
        self,
        region: str,
        field_name: str = "product",
        days: int = 7,
        limit: int = 10,
        min_clusters: int = 2,
    ) -> list[Driver]:
        """
        Get drivers with highest tickets-per-cluster ratio (most duplication).

        Args:
            region: Region to analyze
            field_name: Field to group by
            days: Lookback period in days
            limit: Maximum drivers to return
            min_clusters: Minimum clusters to include

        Returns:
            List of Driver objects ranked by avg_tickets_per_cluster descending
        """
        # Get all drivers
        all_drivers = await self.get_top_drivers(region, field_name, days, limit=100)

        # Filter by minimum clusters and sort by duplication ratio
        filtered = [d for d in all_drivers if d.cluster_count >= min_clusters]
        filtered.sort(key=lambda d: d.avg_tickets_per_cluster, reverse=True)

        return filtered[:limit]

    async def get_summary_stats(
        self,
        region: str,
        days: int = 7,
    ) -> dict:
        """
        Get summary statistics for trend overview.

        Returns:
            Dict with total_clusters, total_tickets, avg_duplication, top_driver
        """
        now = datetime.now(UTC)
        now - timedelta(days=days)

        top_drivers = await self.get_top_drivers(region, "product", days, limit=5)

        total_clusters = sum(d.cluster_count for d in top_drivers)
        total_tickets = sum(d.ticket_count for d in top_drivers)
        avg_duplication = total_tickets / total_clusters if total_clusters > 0 else 0.0

        return {
            "total_clusters": total_clusters,
            "total_tickets": total_tickets,
            "avg_duplication_ratio": round(avg_duplication, 2),
            "top_driver": top_drivers[0].field_value if top_drivers else None,
            "period_days": days,
            "region": region,
        }

    async def _aggregate_by_field(
        self,
        region: str,
        field_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, dict[str, int]]:
        """
        Aggregate cluster and ticket counts by a field value.

        Returns:
            Dict mapping field_value -> {"clusters": int, "tickets": int}
        """
        # Get clusters for the period
        clusters = await self._cluster_repo.get_by_date_range(
            region=region,
            start_date=start_date,
            end_date=end_date,
        )

        aggregation: dict[str, dict[str, int]] = {}

        for cluster in clusters:
            # Get field value from cluster metadata or first ticket
            field_value = await self._get_cluster_field_value(cluster, field_name)
            if not field_value:
                field_value = "Unknown"

            if field_value not in aggregation:
                aggregation[field_value] = {"clusters": 0, "tickets": 0}

            aggregation[field_value]["clusters"] += 1
            aggregation[field_value]["tickets"] += cluster.ticket_count

        return aggregation

    async def _get_cluster_field_value(
        self,
        cluster,
        field_name: str,
    ) -> str | None:
        """
        Get the value of a field from a cluster's representative ticket.

        Uses the first ticket in the cluster to determine the field value.
        """
        if not cluster.ticket_ids:
            return None

        # Get first ticket
        first_ticket_id = cluster.ticket_ids[0]
        ticket = await self._ticket_repo.get_by_id(first_ticket_id)

        if not ticket:
            return None

        # Get field value using getattr for flexibility
        return getattr(ticket, field_name, None)
