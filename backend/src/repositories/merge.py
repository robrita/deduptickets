"""
Merge operation repository for Cosmos DB operations.

Handles merge CRUD and queries with partition key: pk = {year-month}
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from models.merge_operation import MergeOperation, MergeStatus
from repositories.base import BaseRepository

if TYPE_CHECKING:
    from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)


class MergeRepository(BaseRepository[MergeOperation]):
    """Repository for merge operation records."""

    CONTAINER_NAME = "merges"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize merge repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: MergeOperation) -> dict[str, Any]:
        """Convert MergeOperation model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> MergeOperation:
        """Convert Cosmos DB document to MergeOperation model."""
        return MergeOperation.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(timestamp: datetime) -> str:
        """
        Build partition key from timestamp.

        Format: {YYYY-MM}
        """
        return timestamp.strftime("%Y-%m")

    async def get_by_cluster_id(
        self,
        cluster_id: UUID,
        partition_key: str,
    ) -> list[MergeOperation]:
        """
        Get all merge operations for a cluster.

        Args:
            cluster_id: Cluster ID.
            partition_key: Partition key for scoped query.

        Returns:
            List of merge operations.
        """
        query = "SELECT * FROM c WHERE c.clusterId = @cluster_id ORDER BY c.performedAt DESC"
        parameters = [{"name": "@cluster_id", "value": str(cluster_id)}]
        return await self.query(query, parameters, partition_key)

    async def get_by_primary_ticket_id(
        self,
        primary_ticket_id: UUID,
        partition_key: str,
    ) -> list[MergeOperation]:
        """
        Get all merge operations where a ticket is the primary.

        Args:
            primary_ticket_id: Primary ticket ID.
            partition_key: Partition key for scoped query.

        Returns:
            List of merge operations.
        """
        query = """
            SELECT * FROM c
            WHERE c.primaryTicketId = @primary_id
            ORDER BY c.performedAt DESC
        """
        parameters = [{"name": "@primary_id", "value": str(primary_ticket_id)}]
        return await self.query(query, parameters, partition_key)

    async def get_revertible_merges(
        self,
        partition_key: str,
        *,
        limit: int = 100,
    ) -> list[MergeOperation]:
        """
        Get merge operations that can still be reverted.

        Args:
            partition_key: Partition key for scoped query.
            limit: Maximum operations to return.

        Returns:
            List of revertible merge operations.
        """
        query = """
            SELECT * FROM c
            WHERE c.status = @status
            AND c.revertDeadline > @now
            ORDER BY c.performedAt DESC
        """
        parameters = [
            {"name": "@status", "value": MergeStatus.COMPLETED.value},
            {"name": "@now", "value": datetime.now(UTC).isoformat()},
        ]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_pending_merges(
        self,
        partition_key: str,
        *,
        limit: int = 50,
    ) -> list[MergeOperation]:
        """
        Get pending merge operations.

        Args:
            partition_key: Partition key for scoped query.
            limit: Maximum operations to return.

        Returns:
            List of pending merge operations.
        """
        query = "SELECT * FROM c WHERE c.status = @status ORDER BY c.performedAt DESC"
        parameters = [{"name": "@status", "value": MergeStatus.PENDING.value}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def update_status(
        self,
        merge_id: UUID,
        status: MergeStatus,
        partition_key: str,
        *,
        reverted_by: str | None = None,
        reverted_at: datetime | None = None,
        revert_reason: str | None = None,
    ) -> MergeOperation | None:
        """
        Update merge operation status.

        Args:
            merge_id: Merge operation ID.
            status: New status.
            partition_key: Partition key value.
            reverted_by: User who reverted (if applicable).
            reverted_at: Timestamp of revert (if applicable).
            revert_reason: Reason for revert (if applicable).

        Returns:
            Updated merge operation or None if not found.
        """
        merge = await self.get_by_id(merge_id, partition_key)
        if not merge:
            return None

        merge.status = status

        if status == MergeStatus.REVERTED:
            merge.reverted_by = reverted_by
            merge.reverted_at = reverted_at or datetime.now(UTC)
            merge.revert_reason = revert_reason

        return await self.update(merge, partition_key)

    async def get_merged_ticket_ids(
        self,
        primary_ticket_id: UUID,
        partition_key: str,
    ) -> list[UUID]:
        """
        Get all ticket IDs that were merged into a primary ticket.

        Args:
            primary_ticket_id: Primary ticket ID.
            partition_key: Partition key for scoped query.

        Returns:
            List of merged ticket IDs.
        """
        query = """
            SELECT VALUE c.secondaryTicketIds
            FROM c
            WHERE c.primaryTicketId = @primary_id
            AND c.status = @status
        """
        parameters: list[dict[str, object]] = [
            {"name": "@primary_id", "value": str(primary_ticket_id)},
            {"name": "@status", "value": MergeStatus.COMPLETED.value},
        ]

        try:
            items = self._container.query_items(
                query=query,
                parameters=parameters,
                partition_key=partition_key,
            )
            results = [item async for item in items]
        except Exception:
            logger.exception("get_merged_ticket_ids query failed for %s", primary_ticket_id)
            return []
        # Flatten the list of lists
        all_ids: list[UUID] = []
        for ticket_list in results:
            if isinstance(ticket_list, list):
                all_ids.extend(UUID(tid) for tid in ticket_list)
        return all_ids

    async def get_merge_count_by_user(
        self,
        user_id: str,
        partition_key: str | None = None,
    ) -> int:
        """
        Get count of merges performed by a user.

        Args:
            user_id: User ID.
            partition_key: Optional partition key for scoped count.

        Returns:
            Count of merges.
        """
        return await self.count(
            "c.performedBy = @user_id",
            [{"name": "@user_id", "value": user_id}],
            partition_key,
        )

    async def check_revert_conflicts(
        self,
        merge_id: UUID,
        partition_key: str,
    ) -> list[MergeOperation]:
        """
        Check if reverting a merge would conflict with subsequent merges.

        Args:
            merge_id: Merge operation ID to check.
            partition_key: Partition key for scoped query.

        Returns:
            List of conflicting merge operations.
        """
        merge = await self.get_by_id(merge_id, partition_key)
        if not merge:
            return []

        # Find any completed merges that happened after this one
        # involving the same primary ticket
        query = """
            SELECT * FROM c
            WHERE c.primaryTicketId = @primary_id
            AND c.status = @status
            AND c.performedAt > @performed_at
            AND c.id != @merge_id
        """
        parameters = [
            {"name": "@primary_id", "value": str(merge.primary_ticket_id)},
            {"name": "@status", "value": MergeStatus.COMPLETED.value},
            {"name": "@performed_at", "value": merge.performed_at.isoformat()},
            {"name": "@merge_id", "value": str(merge_id)},
        ]
        return await self.query(query, parameters, partition_key)
