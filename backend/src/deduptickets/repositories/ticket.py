"""
Ticket repository for Cosmos DB operations.

Handles ticket CRUD and queries with partition key: pk = {region}|{year-month}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from deduptickets.models.ticket import Ticket
from deduptickets.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy


class TicketRepository(BaseRepository[Ticket]):
    """Repository for ticket operations."""

    CONTAINER_NAME = "tickets"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize ticket repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: Ticket) -> dict[str, Any]:
        """Convert Ticket model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> Ticket:
        """Convert Cosmos DB document to Ticket model."""
        return Ticket.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(region: str, timestamp: datetime) -> str:
        """
        Build partition key from region and timestamp.

        Format: {region}|{YYYY-MM}
        """
        return f"{region}|{timestamp.strftime('%Y-%m')}"

    async def get_by_source_id(self, source_id: str, partition_key: str) -> Ticket | None:
        """
        Get a ticket by its source system ID.

        Args:
            source_id: Source system ticket ID.
            partition_key: Partition key value.

        Returns:
            Ticket if found, None otherwise.
        """
        query = "SELECT * FROM c WHERE c.source_id = @source_id"
        parameters = [{"name": "@source_id", "value": source_id}]

        results = await self.query(query, parameters, partition_key, max_item_count=1)
        return results[0] if results else None

    async def find_similar_tickets(
        self,
        source_system: str,
        product: str,
        severity: str,
        partition_key: str,
        *,
        exclude_ids: list[UUID] | None = None,
        limit: int = 50,
    ) -> list[Ticket]:
        """
        Find tickets with matching fields for clustering analysis.

        Args:
            source_system: Source system to match.
            product: Product to match.
            severity: Severity to match.
            partition_key: Partition key for scoped query.
            exclude_ids: Ticket IDs to exclude.
            limit: Maximum tickets to return.

        Returns:
            List of tickets matching the criteria.
        """
        query = """
            SELECT * FROM c
            WHERE c.source_system = @source_system
            AND c.product = @product
            AND c.severity = @severity
            AND c.cluster_id = null
        """
        parameters = [
            {"name": "@source_system", "value": source_system},
            {"name": "@product", "value": product},
            {"name": "@severity", "value": severity},
        ]

        if exclude_ids:
            exclude_str = ", ".join(f'"{id!s}"' for id in exclude_ids)
            query += f" AND c.id NOT IN ({exclude_str})"

        results = await self.query(query, parameters, partition_key, max_item_count=limit)
        return results

    async def get_unassigned_tickets(
        self,
        partition_key: str,
        *,
        limit: int = 100,
        _offset_token: str | None = None,
    ) -> list[Ticket]:
        """
        Get tickets not yet assigned to a cluster.

        Args:
            partition_key: Partition key for scoped query.
            limit: Maximum tickets to return.
            offset_token: Continuation token for pagination.

        Returns:
            List of unassigned tickets.
        """
        query = "SELECT * FROM c WHERE c.cluster_id = null ORDER BY c.created_at DESC"
        return await self.query(query, partition_key=partition_key, max_item_count=limit)

    async def get_by_cluster_id(
        self,
        cluster_id: UUID,
        partition_key: str,
        *,
        limit: int = 100,
    ) -> list[Ticket]:
        """
        Get all tickets assigned to a specific cluster.

        Args:
            cluster_id: Cluster ID.
            partition_key: Partition key for scoped query.
            limit: Maximum tickets to return.

        Returns:
            List of tickets in the cluster.
        """
        query = "SELECT * FROM c WHERE c.cluster_id = @cluster_id"
        parameters = [{"name": "@cluster_id", "value": str(cluster_id)}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def assign_to_cluster(
        self,
        ticket_id: UUID,
        cluster_id: UUID,
        partition_key: str,
    ) -> Ticket | None:
        """
        Assign a ticket to a cluster.

        Args:
            ticket_id: Ticket ID.
            cluster_id: Cluster ID to assign.
            partition_key: Partition key value.

        Returns:
            Updated ticket or None if not found.
        """
        ticket = await self.get_by_id(ticket_id, partition_key)
        if not ticket:
            return None

        ticket.cluster_id = cluster_id
        ticket.updated_at = datetime.utcnow()
        return await self.update(ticket, partition_key)

    async def remove_from_cluster(
        self,
        ticket_id: UUID,
        partition_key: str,
    ) -> Ticket | None:
        """
        Remove a ticket from its cluster.

        Args:
            ticket_id: Ticket ID.
            partition_key: Partition key value.

        Returns:
            Updated ticket or None if not found.
        """
        ticket = await self.get_by_id(ticket_id, partition_key)
        if not ticket:
            return None

        ticket.cluster_id = None
        ticket.updated_at = datetime.utcnow()
        return await self.update(ticket, partition_key)
