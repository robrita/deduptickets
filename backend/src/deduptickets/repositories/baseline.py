"""
Baseline repository for Cosmos DB operations.

Handles baseline CRUD and queries with partition key: pk = {product}|{year-month}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from deduptickets.models.baseline import Baseline
from deduptickets.repositories.base import BaseRepository

if TYPE_CHECKING:
    from azure.cosmos.aio import ContainerProxy


class BaselineRepository(BaseRepository[Baseline]):
    """Repository for baseline statistics operations."""

    CONTAINER_NAME = "baselines"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize baseline repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: Baseline) -> dict[str, Any]:
        """Convert Baseline model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> Baseline:
        """Convert Cosmos DB document to Baseline model."""
        return Baseline.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(product: str, timestamp: datetime) -> str:
        """
        Build partition key from product and timestamp.

        Format: {product}|{YYYY-MM}
        """
        return f"{product}|{timestamp.strftime('%Y-%m')}"

    async def get_by_product(
        self,
        product: str,
        partition_key: str | None = None,
        *,
        limit: int = 30,
    ) -> list[Baseline]:
        """
        Get baselines for a specific product.

        Args:
            product: Product name.
            partition_key: Optional partition key for scoped query.
            limit: Maximum baselines to return.

        Returns:
            List of baselines ordered by date descending.
        """
        query = "SELECT * FROM c WHERE c.product = @product ORDER BY c.date DESC"
        parameters = [{"name": "@product", "value": product}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_by_product_and_date(
        self,
        product: str,
        date: datetime,
        partition_key: str,
    ) -> Baseline | None:
        """
        Get baseline for a specific product and date.

        Args:
            product: Product name.
            date: Date to look up.
            partition_key: Partition key value.

        Returns:
            Baseline if found, None otherwise.
        """
        date_str = date.strftime("%Y-%m-%d")
        query = """
            SELECT * FROM c
            WHERE c.product = @product
            AND c.date = @date
        """
        parameters = [
            {"name": "@product", "value": product},
            {"name": "@date", "value": date_str},
        ]
        results = await self.query(query, parameters, partition_key, max_item_count=1)
        return results[0] if results else None

    async def get_latest_by_product(
        self,
        product: str,
        partition_key: str | None = None,
    ) -> Baseline | None:
        """
        Get the most recent baseline for a product.

        Args:
            product: Product name.
            partition_key: Optional partition key for scoped query.

        Returns:
            Latest baseline if found, None otherwise.
        """
        query = """
            SELECT TOP 1 * FROM c
            WHERE c.product = @product
            ORDER BY c.date DESC
        """
        parameters = [{"name": "@product", "value": product}]
        results = await self.query(query, parameters, partition_key, max_item_count=1)
        return results[0] if results else None

    async def get_all_products(
        self,
        partition_key: str | None = None,
    ) -> list[str]:
        """
        Get list of all products with baselines.

        Args:
            partition_key: Optional partition key for scoped query.

        Returns:
            List of distinct product names.
        """
        query = "SELECT DISTINCT VALUE c.product FROM c"

        try:
            items = self._container.query_items(
                query=query,
                parameters=[],
                partition_key=partition_key,
            )
            return [item async for item in items]
        except Exception:
            return []

    async def get_date_range(
        self,
        product: str,
        from_date: datetime,
        to_date: datetime,
        partition_key: str | None = None,
    ) -> list[Baseline]:
        """
        Get baselines for a product within a date range.

        Args:
            product: Product name.
            from_date: Start date.
            to_date: End date.
            partition_key: Optional partition key for scoped query.

        Returns:
            List of baselines within the range.
        """
        query = """
            SELECT * FROM c
            WHERE c.product = @product
            AND c.date >= @from_date
            AND c.date <= @to_date
            ORDER BY c.date ASC
        """
        parameters = [
            {"name": "@product", "value": product},
            {"name": "@from_date", "value": from_date.strftime("%Y-%m-%d")},
            {"name": "@to_date", "value": to_date.strftime("%Y-%m-%d")},
        ]
        return await self.query(query, parameters, partition_key)

    async def upsert_baseline(
        self,
        product: str,
        date: datetime,
        *,
        mean_daily_count: float,
        std_deviation: float,
        rolling_window_days: int = 30,
        region: str = "global",
    ) -> Baseline:
        """
        Create or update a baseline for a product and date.

        Args:
            product: Product name.
            date: Date for the baseline.
            mean_daily_count: Calculated mean.
            std_deviation: Calculated standard deviation.
            rolling_window_days: Days used for calculation.
            region: Region for the baseline.

        Returns:
            Created or updated baseline.
        """
        partition_key = self.build_partition_key(product, date)

        existing = await self.get_by_product_and_date(product, date, partition_key)

        if existing:
            existing.mean_daily_count = mean_daily_count
            existing.std_deviation = std_deviation
            existing.rolling_window_days = rolling_window_days
            existing.updated_at = datetime.utcnow()
            return await self.update(existing, partition_key)

        baseline = Baseline(
            product=product,
            region=region,
            date=date,
            mean_daily_count=mean_daily_count,
            std_deviation=std_deviation,
            rolling_window_days=rolling_window_days,
            pk=partition_key,
        )
        return await self.create(baseline, partition_key)

    async def calculate_spike_threshold(
        self,
        product: str,
        partition_key: str,
        *,
        std_multiplier: float = 2.0,
    ) -> float | None:
        """
        Calculate the spike threshold for a product.

        Threshold = mean + (std_multiplier * std_deviation)

        Args:
            product: Product name.
            partition_key: Partition key value.
            std_multiplier: Number of standard deviations.

        Returns:
            Threshold value or None if no baseline exists.
        """
        baseline = await self.get_latest_by_product(product, partition_key)
        if not baseline:
            return None

        return baseline.mean_daily_count + (std_multiplier * baseline.std_deviation)
