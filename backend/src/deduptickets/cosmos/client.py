"""
Async Cosmos DB client singleton.

This module provides a singleton pattern for the Cosmos DB async client,
ensuring connection reuse across requests per SDK best practices.

Constitution Compliance:
- Principle VIII: Async Processing - All operations use async SDK
- Principle I: Security-First - SSL verification configurable, no hardcoded secrets
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

if TYPE_CHECKING:
    from azure.cosmos.aio import ContainerProxy, DatabaseProxy

    from deduptickets.config import Settings

logger = logging.getLogger(__name__)


class CosmosClientManager:
    """
    Manages the async Cosmos DB client lifecycle.

    Implements singleton pattern to reuse client connections across requests.
    SDK best practices: Never recreate CosmosClient instances.
    """

    _instance: CosmosClientManager | None = None
    _client: CosmosClient | None = None
    _database: DatabaseProxy | None = None
    _settings: Settings | None = None

    def __new__(cls) -> CosmosClientManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, settings: Settings) -> None:
        """
        Initialize the Cosmos DB client with settings.

        Args:
            settings: Application settings containing Cosmos DB configuration.
        """
        if self._client is not None:
            logger.debug("Cosmos client already initialized")
            return

        self._settings = settings
        logger.info("Initializing Cosmos DB client for endpoint: %s", settings.cosmos_endpoint)

        # Create client with connection settings
        # Note: SSL verification disabled for Cosmos Emulator (self-signed cert)
        self._client = CosmosClient(
            url=settings.cosmos_endpoint,
            credential=settings.cosmos_key.get_secret_value(),
            connection_verify=settings.cosmos_ssl_verify,
        )

        # Get database reference
        self._database = self._client.get_database_client(settings.cosmos_database)
        logger.info("Cosmos DB client initialized successfully")

    async def close(self) -> None:
        """Close the Cosmos DB client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._database = None
            logger.info("Cosmos DB client closed")

    @property
    def client(self) -> CosmosClient:
        """Get the Cosmos DB client instance."""
        if self._client is None:
            msg = "Cosmos client not initialized. Call initialize() first."
            raise RuntimeError(msg)
        return self._client

    @property
    def database(self) -> DatabaseProxy:
        """Get the database proxy instance."""
        if self._database is None:
            msg = "Cosmos client not initialized. Call initialize() first."
            raise RuntimeError(msg)
        return self._database

    def get_container(self, container_name: str) -> ContainerProxy:
        """
        Get a container proxy by name.

        Args:
            container_name: Name of the container.

        Returns:
            ContainerProxy for the specified container.
        """
        return self.database.get_container_client(container_name)

    async def health_check(self) -> dict[str, str]:
        """
        Perform a health check on the Cosmos DB connection.

        Returns:
            Health status dictionary.

        Raises:
            CosmosHttpResponseError: If connection fails.
        """
        try:
            # Attempt to read database properties as health check
            await self.database.read()
            return {"cosmos": "healthy"}
        except CosmosHttpResponseError as e:
            logger.exception("Cosmos DB health check failed")
            return {"cosmos": "unhealthy", "error": str(e)}


# Global singleton instance
cosmos_manager = CosmosClientManager()


async def get_cosmos_manager() -> CosmosClientManager:
    """
    Dependency injection function for FastAPI.

    Returns:
        The Cosmos client manager singleton.
    """
    return cosmos_manager
