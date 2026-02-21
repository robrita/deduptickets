"""
Ticket repository for Cosmos DB operations.

Handles ticket CRUD and queries with partition key: pk = {year-month}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from models.ticket import Ticket
from repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)


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
    def build_partition_key(timestamp: datetime) -> str:
        """
        Build partition key from timestamp.

        Format: {YYYY-MM}
        """
        return timestamp.strftime("%Y-%m")

    async def get_by_ticket_number(self, ticket_number: str, partition_key: str) -> Ticket | None:
        """
        Get a ticket by its ticket number.

        Args:
            ticket_number: Unique ticket identifier.
            partition_key: Partition key value.

        Returns:
            Ticket if found, None otherwise.
        """
        query = "SELECT * FROM c WHERE c.ticketNumber = @ticket_number"
        parameters = [{"name": "@ticket_number", "value": ticket_number}]

        results = await self.query(query, parameters, partition_key, max_item_count=1)
        return results[0] if results else None

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
        query = "SELECT * FROM c WHERE c.clusterId = null ORDER BY c.createdAt DESC"
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
        query = "SELECT * FROM c WHERE c.clusterId = @cluster_id"
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
        ticket.updated_at = datetime.now(UTC)
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
        ticket.updated_at = datetime.now(UTC)
        return await self.update(ticket, partition_key)
