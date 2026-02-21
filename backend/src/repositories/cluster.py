"""
Cluster repository for Cosmos DB operations.

Handles cluster CRUD and queries with partition key: pk = {year-month}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from azure.cosmos.exceptions import CosmosHttpResponseError

from models.cluster import Cluster, ClusterMember, ClusterStatus
from repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)


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
    def build_partition_key(timestamp: datetime) -> str:
        """
        Build partition key from timestamp.

        Format: {YYYY-MM}
        """
        return timestamp.strftime("%Y-%m")

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
            ORDER BY c.createdAt DESC
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
        query = "SELECT * FROM c WHERE c.status = @status ORDER BY c.createdAt DESC"
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
        query = (
            "SELECT * FROM c WHERE EXISTS("
            "SELECT VALUE m FROM m IN c.members "
            "WHERE m.ticketId = @ticket_id)"
        )
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
        cluster.updated_at = datetime.now(UTC)

        if status == ClusterStatus.DISMISSED:
            cluster.dismissed_by = dismissed_by
            cluster.dismissal_reason = dismissal_reason

        return await self.update(cluster, partition_key)

    async def add_ticket(
        self,
        cluster_id: UUID,
        ticket_id: UUID,
        partition_key: str,
        *,
        ticket_number: str = "",
        summary: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        created_at: datetime | None = None,
        confidence_score: float | None = None,
        max_members: int = 100,
    ) -> Cluster | None:
        """
        Add a ticket to a cluster.

        Args:
            cluster_id: Cluster ID.
            ticket_id: Ticket ID to add.
            partition_key: Partition key value.
            ticket_number: Ticket number for the member record.
            summary: Ticket summary.
            category: Ticket category.
            subcategory: Ticket subcategory.
            created_at: Ticket creation timestamp.
            confidence_score: Confidence score at time of addition.

        Returns:
            Updated cluster or None if not found.
        """
        cluster = await self.get_by_id(cluster_id, partition_key)
        if not cluster:
            return None

        if ticket_id not in cluster.ticket_ids:
            if len(cluster.members) >= max_members:
                msg = f"Cluster member limit ({max_members}) reached"
                raise ValueError(msg)
            cluster.members.append(
                ClusterMember(
                    ticket_id=ticket_id,
                    ticket_number=ticket_number,
                    summary=summary,
                    category=category,
                    subcategory=subcategory,
                    created_at=created_at,
                    confidence_score=confidence_score,
                )
            )
            cluster.ticket_count = len(cluster.members)
            cluster.updated_at = datetime.now(UTC)
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

        if cluster.remove_member(ticket_id):
            return await self.update(cluster, partition_key)

        return cluster

    async def get_by_date_range(
        self,
        *,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
    ) -> list[Cluster]:
        """
        Get clusters within a date range.

        Args:
            start_date: Start of date range.
            end_date: End of date range.
            limit: Maximum clusters to return.

        Returns:
            List of clusters within the date range.
        """
        # Build partition key for the date range (may span multiple months)
        partition_key = self.build_partition_key(end_date)

        query = """
            SELECT * FROM c
            WHERE c.createdAt >= @start_date
            AND c.createdAt <= @end_date
            ORDER BY c.createdAt DESC
        """
        parameters = [
            {"name": "@start_date", "value": start_date.isoformat()},
            {"name": "@end_date", "value": end_date.isoformat()},
        ]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def find_cluster_candidates(
        self,
        *,
        customer_id: str,
        min_updated_at: str,
        query_vector: list[float],
        top_k: int,
        partition_keys: list[str],
        filter_by_customer: bool = True,
        max_members: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Find cluster candidates via VectorDistance search.

        Searches across the given partition keys for clusters matching
        the time window and vector similarity. Optionally filters by customer.
        Excludes clusters that have reached the member capacity cap.

        Args:
            customer_id: Customer ID to scope search.
            min_updated_at: ISO timestamp lower bound.
            query_vector: Embedding vector to compare.
            top_k: Max candidates to return per partition.
            partition_keys: Partition keys to search (e.g. ["2026-02", "2026-01"]).
            filter_by_customer: When True, restrict to matching customerId.
            max_members: Exclude clusters with ticketCount >= this value.

        Returns:
            List of dicts with cluster fields + similarityScore, merged
            across partitions, sorted by similarityScore descending.
        """
        # Build WHERE clauses conditionally
        where_clauses = []
        parameters: list[dict[str, Any]] = [
            {"name": "@topK", "value": top_k},
            {"name": "@queryVector", "value": query_vector},
            {"name": "@minUpdatedAt", "value": min_updated_at},
            {"name": "@maxMembers", "value": max_members},
        ]

        if filter_by_customer:
            where_clauses.append("c.customerId = @customerId")
            parameters.append({"name": "@customerId", "value": customer_id})

        where_clauses.append("c.updatedAt >= @minUpdatedAt")
        where_clauses.append("c.openCount > 0")
        where_clauses.append("c.ticketCount < @maxMembers")

        where_str = " AND ".join(where_clauses)

        query = (
            "SELECT TOP @topK "  # noqa: S608  # nosec B608
            "c.id, c.customerId, c.openCount, c.category, c.subcategory, "
            "c.updatedAt, c.ticketCount, c.status, c.pk, "
            "VectorDistance(c.centroidVector, @queryVector) AS similarityScore "
            "FROM c "
            f"WHERE {where_str} "
            "ORDER BY VectorDistance(c.centroidVector, @queryVector)"
        )

        all_results: list[dict[str, Any]] = []
        for pk in partition_keys:
            try:
                items = self._container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=pk,
                )
                results = [item async for item in items]
                all_results.extend(results)
            except CosmosHttpResponseError:
                logger.exception("Vector search failed for partition %s", pk)

        # Sort merged results by similarity descending, take top_k
        all_results.sort(key=lambda x: x.get("similarityScore", 0), reverse=True)
        return all_results[:top_k]

    async def update_cluster_with_etag(
        self,
        cluster: Cluster,
    ) -> Cluster:
        """
        Update a cluster with ETag-based optimistic concurrency.

        Uses replace_item with if_match to prevent lost updates
        during concurrent centroid vector modifications.

        Args:
            cluster: Cluster model with updated fields. Must have etag set.

        Returns:
            Updated cluster.

        Raises:
            CosmosHttpResponseError: On ETag conflict (412) or other errors.
        """
        document = self._to_document(cluster)
        result = await self._container.replace_item(
            item=str(cluster.id),
            body=document,
            if_match=cluster.etag,
        )
        return self._from_document(result)
