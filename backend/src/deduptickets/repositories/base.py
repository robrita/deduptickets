"""
Abstract base repository for Cosmos DB operations.

Provides common CRUD operations with Cosmos DB best practices:
- Async operations (Constitution Principle VIII)
- Proper error handling and logging
- Reusable query patterns
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from pydantic import BaseModel

if TYPE_CHECKING:
    from uuid import UUID

    from azure.cosmos.aio import ContainerProxy

logger = logging.getLogger(__name__)

# Generic type for domain models
T = TypeVar("T", bound=BaseModel)


class BaseRepository[T: BaseModel](ABC):
    """
    Abstract base repository for Cosmos DB container operations.

    Provides common CRUD patterns with proper error handling and logging.
    Subclasses must implement document conversion methods.
    """

    def __init__(self, container: ContainerProxy, container_name: str) -> None:
        """
        Initialize the repository.

        Args:
            container: Cosmos DB container proxy.
            container_name: Name of the container (for logging).
        """
        self._container = container
        self._container_name = container_name

    @property
    def container(self) -> ContainerProxy:
        """Get the container proxy."""
        return self._container

    @abstractmethod
    def _to_document(self, entity: T) -> dict[str, Any]:
        """Convert domain model to Cosmos DB document."""
        ...

    @abstractmethod
    def _from_document(self, doc: dict[str, Any]) -> T:
        """Convert Cosmos DB document to domain model."""
        ...

    async def create(self, entity: T, _partition_key: str) -> T:
        """
        Create a new document in the container.

        Args:
            entity: Domain model to create.
            partition_key: Partition key value.

        Returns:
            Created entity with any server-generated fields.

        Raises:
            CosmosHttpResponseError: If creation fails.
        """
        document = self._to_document(entity)
        logger.debug("Creating document in %s: %s", self._container_name, document.get("id"))

        try:
            result = await self._container.create_item(
                body=document,
                enable_automatic_id_generation=False,
            )
            logger.info("Created document %s in %s", result["id"], self._container_name)
            return self._from_document(result)
        except CosmosHttpResponseError:
            logger.exception("Failed to create document in %s", self._container_name)
            raise

    async def get_by_id(self, item_id: UUID | str, partition_key: str) -> T | None:
        """
        Get a document by ID (point read - ~1 RU).

        Args:
            item_id: Document ID.
            partition_key: Partition key value.

        Returns:
            Domain model if found, None otherwise.
        """
        str_id = str(item_id)
        logger.debug("Reading document %s from %s", str_id, self._container_name)

        try:
            result = await self._container.read_item(
                item=str_id,
                partition_key=partition_key,
            )
            return self._from_document(result)
        except CosmosResourceNotFoundError:
            logger.debug("Document %s not found in %s", str_id, self._container_name)
            return None
        except CosmosHttpResponseError:
            logger.exception("Failed to read document %s from %s", str_id, self._container_name)
            raise

    async def update(self, entity: T, _partition_key: str) -> T:
        """
        Update (upsert) a document.

        Args:
            entity: Domain model with updated values.
            partition_key: Partition key value.

        Returns:
            Updated entity.

        Raises:
            CosmosHttpResponseError: If update fails.
        """
        document = self._to_document(entity)
        logger.debug("Updating document %s in %s", document.get("id"), self._container_name)

        try:
            result = await self._container.upsert_item(body=document)
            logger.info("Updated document %s in %s", result["id"], self._container_name)
            return self._from_document(result)
        except CosmosHttpResponseError:
            logger.exception("Failed to update document in %s", self._container_name)
            raise

    async def delete(self, item_id: UUID | str, partition_key: str) -> bool:
        """
        Delete a document.

        Args:
            item_id: Document ID.
            partition_key: Partition key value.

        Returns:
            True if deleted, False if not found.
        """
        str_id = str(item_id)
        logger.debug("Deleting document %s from %s", str_id, self._container_name)

        try:
            await self._container.delete_item(
                item=str_id,
                partition_key=partition_key,
            )
            logger.info("Deleted document %s from %s", str_id, self._container_name)
            return True
        except CosmosResourceNotFoundError:
            logger.debug("Document %s not found for deletion in %s", str_id, self._container_name)
            return False
        except CosmosHttpResponseError:
            logger.exception("Failed to delete document %s from %s", str_id, self._container_name)
            raise

    async def query(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
        *,
        max_item_count: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """
        Execute a SQL query and return results.

        Args:
            query: Cosmos DB SQL query string.
            parameters: Query parameters.
            partition_key: Optional partition key for scoped query.
            max_item_count: Maximum items to return (LIMIT).
            offset: Number of items to skip (OFFSET).

        Returns:
            List of domain models matching the query.
        """
        logger.debug("Executing query on %s: %s", self._container_name, query[:100])

        # Add OFFSET/LIMIT if not already in query
        optimized_query = query
        if "OFFSET" not in query.upper() and "LIMIT" not in query.upper():
            optimized_query = f"{query} OFFSET {offset} LIMIT {max_item_count}"

        try:
            items = self._container.query_items(
                query=optimized_query,
                parameters=parameters or [],
                partition_key=partition_key,
                max_item_count=max_item_count,
            )
            results = [self._from_document(item) async for item in items]
            logger.debug("Query returned %d items from %s", len(results), self._container_name)
            return results
        except CosmosHttpResponseError:
            logger.exception("Query failed on %s", self._container_name)
            raise

    async def query_with_projection(
        self,
        fields: list[str],
        where_clause: str | None = None,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
        *,
        max_item_count: int = 100,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a query with field projection to reduce RU cost.

        Projection reduces data transfer and RU consumption by only
        fetching requested fields instead of entire documents.

        Args:
            fields: List of field names to project (e.g., ["id", "status", "createdAt"]).
            where_clause: Optional WHERE clause (without WHERE keyword).
            parameters: Query parameters.
            partition_key: Optional partition key for scoped query.
            max_item_count: Maximum items to return.
            offset: Number of items to skip.
            order_by: Optional ORDER BY clause (e.g., "c.createdAt DESC").

        Returns:
            List of dictionaries with only projected fields.
        """
        # Build SELECT projection
        projection = ", ".join(f"c.{field}" for field in fields)
        query = f"SELECT {projection} FROM c"  # noqa: S608

        if where_clause:
            query = f"{query} WHERE {where_clause}"

        if order_by:
            query = f"{query} ORDER BY {order_by}"

        query = f"{query} OFFSET {offset} LIMIT {max_item_count}"

        logger.debug("Executing projected query on %s: %s", self._container_name, query[:100])

        try:
            items = self._container.query_items(
                query=query,
                parameters=parameters or [],
                partition_key=partition_key,
                max_item_count=max_item_count,
            )
            results = [item async for item in items]
            logger.debug(
                "Projected query returned %d items from %s",
                len(results),
                self._container_name,
            )
            return results
        except CosmosHttpResponseError:
            logger.exception("Projected query failed on %s", self._container_name)
            raise

    async def count(
        self,
        query: str | None = None,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> int:
        """
        Count documents matching a query.

        Args:
            query: Optional WHERE clause (without SELECT).
            parameters: Query parameters.
            partition_key: Optional partition key for scoped count.

        Returns:
            Count of matching documents.
        """
        count_query = "SELECT VALUE COUNT(1) FROM c"
        if query:
            count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {query}"  # noqa: S608

        try:
            items = self._container.query_items(
                query=count_query,
                parameters=parameters or [],
                partition_key=partition_key,
            )
            result = [item async for item in items]
            return result[0] if result else 0
        except CosmosHttpResponseError:
            logger.exception("Count query failed on %s", self._container_name)
            raise
