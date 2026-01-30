"""
Cluster repository for Cosmos DB operations.

Handles cluster CRUD and queries with partition key: pk = {region}|{year-month}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from deduptickets.models.cluster import Cluster, ClusterStatus
from deduptickets.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy


class ClusterRepository(BaseRepository[Cluster]):
    """Repository for cluster operations."""

    CONTAINER_NAME = "clusters"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize cluster repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: Cluster) -> dict[str, Any]:
        """Convert Cluster model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> Cluster:
        """Convert Cosmos DB document to Cluster model."""
        return Cluster.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(region: str, timestamp: datetime) -> str:
        """
        Build partition key from region and timestamp.

        Format: {region}|{YYYY-MM}
        """
        return f"{region}|{timestamp.strftime('%Y-%m')}"

    async def get_pending_clusters(
        self,
        partition_key: str,
        *,
        limit: int = 100,
    ) -> list[Cluster]:
        """
        Get clusters pending review.

        Args:
            partition_key: Partition key for scoped query.
            limit: Maximum clusters to return.

        Returns:
            List of pending clusters.
        """
        query = """
            SELECT * FROM c
            WHERE c.status = @status
            ORDER BY c.confidence_score DESC, c.created_at DESC
        """
        parameters = [{"name": "@status", "value": ClusterStatus.PENDING.value}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_pending_review_count(self, partition_key: str | None = None) -> int:
        """
        Get count of clusters pending review.

        Args:
            partition_key: Optional partition key for scoped count.

        Returns:
            Count of pending clusters.
        """
        return await self.count(
            "c.status = @status",
            [{"name": "@status", "value": ClusterStatus.PENDING.value}],
            partition_key,
        )

    async def get_by_status(
        self,
        status: ClusterStatus,
        partition_key: str | None = None,
        *,
        limit: int = 100,
    ) -> list[Cluster]:
        """
        Get clusters by status.

        Args:
            status: Cluster status to filter by.
            partition_key: Optional partition key for scoped query.
            limit: Maximum clusters to return.

        Returns:
            List of clusters with the specified status.
        """
        query = "SELECT * FROM c WHERE c.status = @status ORDER BY c.created_at DESC"
        parameters = [{"name": "@status", "value": status.value}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_clusters_with_ticket(
        self,
        ticket_id: UUID,
        partition_key: str,
    ) -> list[Cluster]:
        """
        Get clusters containing a specific ticket.

        Args:
            ticket_id: Ticket ID to search for.
            partition_key: Partition key for scoped query.

        Returns:
            List of clusters containing the ticket.
        """
        query = "SELECT * FROM c WHERE ARRAY_CONTAINS(c.ticket_ids, @ticket_id)"
        parameters = [{"name": "@ticket_id", "value": str(ticket_id)}]
        return await self.query(query, parameters, partition_key)

    async def update_status(
        self,
        cluster_id: UUID,
        status: ClusterStatus,
        partition_key: str,
        *,
        dismissed_by: str | None = None,
        dismissal_reason: str | None = None,
    ) -> Cluster | None:
        """
        Update cluster status.

        Args:
            cluster_id: Cluster ID.
            status: New status.
            partition_key: Partition key value.
            dismissed_by: User who dismissed (if applicable).
            dismissal_reason: Reason for dismissal (if applicable).

        Returns:
            Updated cluster or None if not found.
        """
        cluster = await self.get_by_id(cluster_id, partition_key)
        if not cluster:
            return None

        cluster.status = status
        cluster.updated_at = datetime.utcnow()

        if status == ClusterStatus.DISMISSED:
            cluster.dismissed_by = dismissed_by
            cluster.dismissal_reason = dismissal_reason

        return await self.update(cluster, partition_key)

    async def add_ticket(
        self,
        cluster_id: UUID,
        ticket_id: UUID,
        partition_key: str,
    ) -> Cluster | None:
        """
        Add a ticket to a cluster.

        Args:
            cluster_id: Cluster ID.
            ticket_id: Ticket ID to add.
            partition_key: Partition key value.

        Returns:
            Updated cluster or None if not found.
        """
        cluster = await self.get_by_id(cluster_id, partition_key)
        if not cluster:
            return None

        if ticket_id not in cluster.ticket_ids:
            cluster.ticket_ids.append(ticket_id)
            cluster.ticket_count = len(cluster.ticket_ids)
            cluster.updated_at = datetime.utcnow()
            return await self.update(cluster, partition_key)

        return cluster

    async def remove_ticket(
        self,
        cluster_id: UUID,
        ticket_id: UUID,
        partition_key: str,
    ) -> Cluster | None:
        """
        Remove a ticket from a cluster.

        Args:
            cluster_id: Cluster ID.
            ticket_id: Ticket ID to remove.
            partition_key: Partition key value.

        Returns:
            Updated cluster or None if not found.
        """
        cluster = await self.get_by_id(cluster_id, partition_key)
        if not cluster:
            return None

        if ticket_id in cluster.ticket_ids:
            cluster.ticket_ids.remove(ticket_id)
            cluster.ticket_count = len(cluster.ticket_ids)
            cluster.updated_at = datetime.utcnow()
            return await self.update(cluster, partition_key)

        return cluster

    async def get_high_confidence_clusters(
        self,
        min_confidence: float,
        partition_key: str | None = None,
        *,
        limit: int = 50,
    ) -> list[Cluster]:
        """
        Get clusters above a confidence threshold.

        Args:
            min_confidence: Minimum confidence score (0.0-1.0).
            partition_key: Optional partition key for scoped query.
            limit: Maximum clusters to return.

        Returns:
            List of high-confidence clusters.
        """
        query = """
            SELECT * FROM c
            WHERE c.confidence_score >= @min_confidence
            AND c.status = @status
            ORDER BY c.confidence_score DESC
        """
        parameters = [
            {"name": "@min_confidence", "value": min_confidence},
            {"name": "@status", "value": ClusterStatus.PENDING.value},
        ]
        return await self.query(query, parameters, partition_key, max_item_count=limit)
