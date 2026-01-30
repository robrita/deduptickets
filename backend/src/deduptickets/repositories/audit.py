"""
Audit repository for Cosmos DB operations.

Handles audit log CRUD and queries with partition key: pk = {entity_type}|{year-month}
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from deduptickets.models.audit_entry import AuditAction, AuditEntry
from deduptickets.repositories.base import BaseRepository

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy


class AuditRepository(BaseRepository[AuditEntry]):
    """Repository for audit log operations."""

    CONTAINER_NAME = "audit"

    def __init__(self, container: ContainerProxy) -> None:
        """Initialize audit repository."""
        super().__init__(container, self.CONTAINER_NAME)

    def _to_document(self, entity: AuditEntry) -> dict[str, Any]:
        """Convert AuditEntry model to Cosmos DB document."""
        return entity.to_cosmos_document()

    def _from_document(self, doc: dict[str, Any]) -> AuditEntry:
        """Convert Cosmos DB document to AuditEntry model."""
        return AuditEntry.from_cosmos_document(doc)

    @staticmethod
    def build_partition_key(entity_type: str, timestamp: datetime) -> str:
        """
        Build partition key from entity type and timestamp.

        Format: {entity_type}|{YYYY-MM}
        """
        return f"{entity_type}|{timestamp.strftime('%Y-%m')}"

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        partition_key: str,
        *,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Get audit entries for a specific entity.

        Args:
            entity_type: Type of entity (ticket, cluster, merge).
            entity_id: Entity ID.
            partition_key: Partition key for scoped query.
            limit: Maximum entries to return.

        Returns:
            List of audit entries.
        """
        query = """
            SELECT * FROM c
            WHERE c.entity_type = @entity_type
            AND c.entity_id = @entity_id
            ORDER BY c.timestamp DESC
        """
        parameters = [
            {"name": "@entity_type", "value": entity_type},
            {"name": "@entity_id", "value": str(entity_id)},
        ]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_by_user(
        self,
        user_id: str,
        partition_key: str | None = None,
        *,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Get audit entries for a specific user.

        Args:
            user_id: User ID.
            partition_key: Optional partition key for scoped query.
            limit: Maximum entries to return.

        Returns:
            List of audit entries.
        """
        query = "SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c.timestamp DESC"
        parameters = [{"name": "@user_id", "value": user_id}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_by_action(
        self,
        action: AuditAction,
        partition_key: str | None = None,
        *,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Get audit entries for a specific action type.

        Args:
            action: Audit action type.
            partition_key: Optional partition key for scoped query.
            limit: Maximum entries to return.

        Returns:
            List of audit entries.
        """
        query = "SELECT * FROM c WHERE c.action = @action ORDER BY c.timestamp DESC"
        parameters = [{"name": "@action", "value": action.value}]
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def get_recent_entries(
        self,
        partition_key: str | None = None,
        *,
        hours: int = 24,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Get recent audit entries within a time window.

        Args:
            partition_key: Optional partition key for scoped query.
            hours: Number of hours to look back.
            limit: Maximum entries to return.

        Returns:
            List of recent audit entries.
        """
        from_time = (
            datetime.utcnow().replace(hour=datetime.utcnow().hour - hours).isoformat()
            if hours < 24
            else None
        )

        query = "SELECT * FROM c"
        parameters = []

        if from_time:
            query += " WHERE c.timestamp >= @from_time"
            parameters.append({"name": "@from_time", "value": from_time})

        query += " ORDER BY c.timestamp DESC"
        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def search(
        self,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        user_id: str | None = None,
        action: AuditAction | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        partition_key: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Search audit entries with multiple filters.

        Args:
            entity_type: Filter by entity type.
            entity_id: Filter by entity ID.
            user_id: Filter by user ID.
            action: Filter by action type.
            from_date: Filter from this date.
            to_date: Filter until this date.
            partition_key: Optional partition key for scoped query.
            limit: Maximum entries to return.

        Returns:
            List of matching audit entries.
        """
        conditions = []
        parameters = []

        if entity_type:
            conditions.append("c.entity_type = @entity_type")
            parameters.append({"name": "@entity_type", "value": entity_type})

        if entity_id:
            conditions.append("c.entity_id = @entity_id")
            parameters.append({"name": "@entity_id", "value": str(entity_id)})

        if user_id:
            conditions.append("c.user_id = @user_id")
            parameters.append({"name": "@user_id", "value": user_id})

        if action:
            conditions.append("c.action = @action")
            parameters.append({"name": "@action", "value": action.value})

        if from_date:
            conditions.append("c.timestamp >= @from_date")
            parameters.append({"name": "@from_date", "value": from_date.isoformat()})

        if to_date:
            conditions.append("c.timestamp <= @to_date")
            parameters.append({"name": "@to_date", "value": to_date.isoformat()})

        query = "SELECT * FROM c"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY c.timestamp DESC"

        return await self.query(query, parameters, partition_key, max_item_count=limit)

    async def log_action(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        action: AuditAction,
        user_id: str,
        user_ip: str | None = None,
        user_agent: str | None = None,
        changes: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """
        Create a new audit log entry.

        Args:
            entity_type: Type of entity being audited.
            entity_id: ID of the entity.
            action: Action performed.
            user_id: User who performed the action.
            user_ip: Client IP address.
            user_agent: Client user agent.
            changes: Dictionary of field changes (before/after).
            metadata: Additional context.

        Returns:
            Created audit entry.
        """
        timestamp = datetime.utcnow()
        partition_key = self.build_partition_key(entity_type, timestamp)

        entry = AuditEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            timestamp=timestamp,
            user_ip=user_ip,
            user_agent=user_agent,
            changes=changes or {},
            metadata=metadata or {},
            pk=partition_key,
        )

        return await self.create(entry, partition_key)

    async def get_action_count(
        self,
        action: AuditAction,
        partition_key: str | None = None,
    ) -> int:
        """
        Get count of a specific action type.

        Args:
            action: Action type to count.
            partition_key: Optional partition key for scoped count.

        Returns:
            Count of actions.
        """
        return await self.count(
            "c.action = @action",
            [{"name": "@action", "value": action.value}],
            partition_key,
        )
