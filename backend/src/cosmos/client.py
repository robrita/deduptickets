"""
Async Cosmos DB client singleton with lazy initialization.

This module provides a singleton pattern for the Cosmos DB async client,
ensuring connection reuse across requests per SDK best practices.
The client connects lazily on first data access, not at startup.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError

if TYPE_CHECKING:
    from azure.cosmos.aio import ContainerProxy, DatabaseProxy

    from config import Settings

logger = logging.getLogger(__name__)


class CosmosClientManager:
    """
    Manages the async Cosmos DB client lifecycle.

    Implements singleton pattern to reuse client connections across requests.
    SDK best practices: Never recreate CosmosClient instances.

    Supports lazy initialization: call configure() at startup (no network),
    then the first data access triggers the actual connection.
    """

    _instance: CosmosClientManager | None = None
    _client: CosmosClient | None = None
    _database: DatabaseProxy | None = None
    _settings: Settings | None = None
    _credential: Any = None
    _initialized: bool = False
    _init_lock: asyncio.Lock | None = None

    def __new__(cls) -> CosmosClientManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._init_lock = asyncio.Lock()
        return cls._instance

    def configure(self, settings: Settings) -> None:
        """
        Store settings for later lazy initialization. No network call.

        Args:
            settings: Application settings containing Cosmos DB configuration.
        """
        self._settings = settings
        logger.info(
            "Cosmos DB configured for endpoint: %s (not yet connected)",
            settings.cosmos_endpoint,
        )

    @property
    def is_configured(self) -> bool:
        """Whether settings have been provided via configure()."""
        return self._settings is not None

    @property
    def is_connected(self) -> bool:
        """Whether the Cosmos DB client is connected."""
        return self._client is not None and self._initialized

    async def _ensure_initialized(self) -> None:
        """
        Lazily initialize the Cosmos DB client on first access.

        Thread-safe via asyncio.Lock. Idempotent — subsequent calls are no-ops.

        Raises:
            RuntimeError: If configure() was not called first.
            Exception: If the Cosmos DB connection fails.
        """
        if self._initialized:
            return

        if self._settings is None:
            msg = "Cosmos DB not configured. Call configure(settings) first."
            raise RuntimeError(msg)

        # Lazy-create lock if needed (e.g. after singleton reset in tests)
        if self._init_lock is None:
            self._init_lock = asyncio.Lock()

        async with self._init_lock:
            # Double-check after acquiring lock
            if self._initialized:
                return

            settings = self._settings
            logger.info("Initializing Cosmos DB client for endpoint: %s", settings.cosmos_endpoint)

            if settings.cosmos_use_aad:
                from azure.identity.aio import DefaultAzureCredential  # noqa: PLC0415

                self._credential = DefaultAzureCredential()
                credential: Any = self._credential
                logger.info("Using Microsoft Entra ID (AAD) authentication")
            else:
                if not settings.cosmos_key:
                    msg = (
                        "Cosmos DB account key not configured. "
                        "Set COSMOS_KEY or use COSMOS_USE_AAD=true."
                    )
                    raise RuntimeError(msg)
                credential = settings.cosmos_key.get_secret_value()
                logger.info("Using account key authentication")

            self._client = CosmosClient(
                url=settings.cosmos_endpoint,
                credential=credential,
                connection_verify=settings.cosmos_ssl_verify,
            )
            self._database = self._client.get_database_client(settings.cosmos_database)
            self._initialized = True
            logger.info("Cosmos DB client initialized successfully")

    async def initialize(self, settings: Settings) -> None:
        """
        Eagerly initialize the Cosmos DB client.

        Provided for backward compatibility. Prefer configure() + lazy access.

        Args:
            settings: Application settings containing Cosmos DB configuration.
        """
        self.configure(settings)
        await self._ensure_initialized()

    async def close(self) -> None:
        """Close the Cosmos DB client connection and AAD credential if used."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            self._database = None
            self._initialized = False
            logger.info("Cosmos DB client closed")
        if self._credential is not None:
            await self._credential.close()
            self._credential = None

    @property
    def client(self) -> CosmosClient:
        """Get the Cosmos DB client instance."""
        if self._client is None:
            msg = "Cosmos client not initialized. Call _ensure_initialized() first."
            raise RuntimeError(msg)
        return self._client

    @property
    def database(self) -> DatabaseProxy:
        """Get the database proxy instance."""
        if self._database is None:
            msg = "Cosmos client not initialized. Call _ensure_initialized() first."
            raise RuntimeError(msg)
        return self._database

    async def get_container(self, container_name: str) -> ContainerProxy:
        """
        Get a container proxy by name, initializing the client if needed.

        Args:
            container_name: Name of the container.

        Returns:
            ContainerProxy for the specified container.
        """
        await self._ensure_initialized()
        return self.database.get_container_client(container_name)

    async def health_check(self) -> dict[str, str]:
        """
        Perform a health check on the Cosmos DB connection.

        Returns:
            Health status dictionary.
        """
        if not self.is_configured:
            return {"cosmos": "not_configured"}

        if not self.is_connected:
            return {"cosmos": "not_connected"}

        try:
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
