"""
Spike alert repository for Cosmos DB operations.

Handles spike alert CRUD and queries with partition key: pk = {region}|{year-month}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from deduptickets.models.spike_alert import SpikeAlert, SpikeStatus
from deduptickets.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy


class SpikeRepository(BaseRepository[SpikeAlert]):
    """Repository for spike alert operations."""

    CONTAINER_NAME = "spikes"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize spike repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: SpikeAlert) -> dict[str, Any]:
        """Convert SpikeAlert model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> SpikeAlert:
        """Convert Cosmos DB document to SpikeAlert model."""
        return SpikeAlert.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(region: str, timestamp: datetime) -> str:
        """
        Build partition key from region and timestamp.

        Format: {region}|{YYYY-MM}
        """
        return f"{region}|{timestamp.strftime('%Y-%m')}"

    async def get_active_spikes(
        self,
        partition_key: str | None = None,
        *,
        limit: int = 50,
    ) -> list[SpikeAlert]:
        """
        Get active spike alerts.

        Args:
            partition_key: Optional partition key for scoped query.
            limit: Maximum alerts to return.

        Returns:
            List of active spike alerts.
        """
        query = """
            SELECT * FROM c
            WHERE c.status = @status
            ORDER BY c.deviation_percent DESC, c.detected_at DESC
        """
        parameters = [{"name": "@status", "value": SpikeStatus.ACTIVE.value}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_by_product(
        self,
        product: str,
        partition_key: str | None = None,
        *,
        limit: int = 50,
    ) -> list[SpikeAlert]:
        """
        Get spike alerts for a specific product.

        Args:
            product: Product name.
            partition_key: Optional partition key for scoped query.
            limit: Maximum alerts to return.

        Returns:
            List of spike alerts.
        """
        query = "SELECT * FROM c WHERE c.product = @product ORDER BY c.detected_at DESC"
        parameters = [{"name": "@product", "value": product}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_recent_spikes(
        self,
        partition_key: str | None = None,
        *,
        hours: int = 24,
        limit: int = 50,
    ) -> list[SpikeAlert]:
        """
        Get spike alerts from the last N hours.

        Args:
            partition_key: Optional partition key for scoped query.
            hours: Number of hours to look back.
            limit: Maximum alerts to return.

        Returns:
            List of recent spike alerts.
        """
        from_time = datetime.utcnow()
        from_time = from_time.replace(hour=max(0, from_time.hour - hours % 24))

        query = """
            SELECT * FROM c
            WHERE c.detected_at >= @from_time
            ORDER BY c.deviation_percent DESC, c.detected_at DESC
        """
        parameters = [{"name": "@from_time", "value": from_time.isoformat()}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def acknowledge(
        self,
        spike_id: UUID,
        partition_key: str,
        *,
        acknowledged_by: str,
    ) -> SpikeAlert | None:
        """
        Acknowledge a spike alert.

        Args:
            spike_id: Spike alert ID.
            partition_key: Partition key value.
            acknowledged_by: User who acknowledged.

        Returns:
            Updated spike alert or None if not found.
        """
        spike = await self.get_by_id(spike_id, partition_key)
        if not spike:
            return None

        spike.status = SpikeStatus.ACKNOWLEDGED
        spike.acknowledged_by = acknowledged_by
        spike.acknowledged_at = datetime.utcnow()

        return await self.update(spike, partition_key)

    async def resolve(
        self,
        spike_id: UUID,
        partition_key: str,
        *,
        resolved_by: str,
        resolution_notes: str | None = None,
    ) -> SpikeAlert | None:
        """
        Resolve a spike alert.

        Args:
            spike_id: Spike alert ID.
            partition_key: Partition key value.
            resolved_by: User who resolved.
            resolution_notes: Resolution notes.

        Returns:
            Updated spike alert or None if not found.
        """
        spike = await self.get_by_id(spike_id, partition_key)
        if not spike:
            return None

        spike.status = SpikeStatus.RESOLVED
        spike.resolved_by = resolved_by
        spike.resolved_at = datetime.utcnow()
        if resolution_notes:
            spike.resolution_notes = resolution_notes

        return await self.update(spike, partition_key)

    async def get_by_severity(
        self,
        severity: str,
        partition_key: str | None = None,
        *,
        limit: int = 50,
    ) -> list[SpikeAlert]:
        """
        Get spike alerts by severity level.

        Args:
            severity: Severity level (e.g., critical, high, medium, low).
            partition_key: Optional partition key for scoped query.
            limit: Maximum alerts to return.

        Returns:
            List of spike alerts.
        """
        query = """
            SELECT * FROM c
            WHERE c.severity = @severity
            ORDER BY c.detected_at DESC
        """
        parameters = [{"name": "@severity", "value": severity}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_active_count(self, partition_key: str | None = None) -> int:
        """
        Get count of active spike alerts.

        Args:
            partition_key: Optional partition key for scoped count.

        Returns:
            Count of active spikes.
        """
        return await self.count(
            "c.status = @status",
            [{"name": "@status", "value": SpikeStatus.ACTIVE.value}],
            partition_key,
        )

    async def auto_resolve_old_spikes(
        self,
        partition_key: str,
        *,
        older_than_hours: int = 72,
    ) -> int:
        """
        Auto-resolve spike alerts older than a threshold.

        Args:
            partition_key: Partition key for scoped query.
            older_than_hours: Age threshold in hours.

        Returns:
            Count of resolved spikes.
        """
        threshold = datetime.utcnow()
        threshold = threshold.replace(hour=max(0, threshold.hour - older_than_hours % 24))

        query = """
            SELECT * FROM c
            WHERE c.status = @status
            AND c.detected_at < @threshold
        """
        parameters = [
            {"name": "@status", "value": SpikeStatus.ACTIVE.value},
            {"name": "@threshold", "value": threshold.isoformat()},
        ]

        old_spikes = await self.query(query, parameters, partition_key)
        count = 0

        for spike in old_spikes:
            spike.status = SpikeStatus.AUTO_RESOLVED
            spike.resolved_at = datetime.utcnow()
            await self.update(spike, partition_key)
            count += 1

        return count
