"""
Cosmos DB database and container setup script.

Creates the database and all required containers with proper partition keys
and indexing policies as defined in data-model.md.

Run standalone:
    python -m cosmos.setup        (from backend/src/)
    make db-setup                 (from project root)

Constitution Compliance:
- Principle V: Performance Budgets - Composite indexes for common query patterns
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import TYPE_CHECKING, Any

from azure.cosmos import PartitionKey
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceExistsError

if TYPE_CHECKING:
    from azure.cosmos.aio import DatabaseProxy

logger = logging.getLogger(__name__)

# TTL constants (seconds)
TTL_DISABLED = -1  # Container-level TTL enabled but items don't expire by default
TTL_90_DAYS = 90 * 24 * 60 * 60  # 7 776 000 s
TTL_180_DAYS = 180 * 24 * 60 * 60  # 15 552 000 s

# Container configurations per data-model.md
CONTAINERS = {
    "tickets": {
        "partition_key": "/pk",
        "default_ttl": TTL_DISABLED,
        "unique_key_policy": {
            "uniqueKeys": [
                {"paths": ["/ticketNumber"]},
            ],
        },
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/*"},
            ],
            "excludedPaths": [
                {"path": "/description/*"},
                {"path": "/name/*"},
                {"path": "/mobileNumber/*"},
                {"path": "/email/*"},
                {"path": "/rawMetadata/*"},
                {"path": "/contentVector/*"},
                {"path": "/dedupText/*"},
                {"path": "/dedup/*"},
                {"path": "/_etag/?"},
            ],
            "compositeIndexes": [
                [
                    {"path": "/status", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
                [
                    {"path": "/category", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
                [
                    {"path": "/merchant", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
            ],
            "vectorIndexes": [
                {"path": "/contentVector", "type": "diskANN"},
            ],
        },
        "vector_embedding_policy": {
            "vectorEmbeddings": [
                {
                    "path": "/contentVector",
                    "dataType": "float32",
                    "distanceFunction": "cosine",
                    "dimensions": 1536,
                },
            ],
        },
    },
    "clusters": {
        "partition_key": "/pk",
        "default_ttl": TTL_DISABLED,
        "unique_key_policy": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/*"},
            ],
            "excludedPaths": [
                {"path": "/members/*"},
                {"path": "/centroidVector/*"},
                {"path": "/_etag/?"},
            ],
            "compositeIndexes": [
                [
                    {"path": "/status", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
            ],
            "vectorIndexes": [
                {"path": "/centroidVector", "type": "diskANN"},
            ],
        },
        "vector_embedding_policy": {
            "vectorEmbeddings": [
                {
                    "path": "/centroidVector",
                    "dataType": "float32",
                    "distanceFunction": "cosine",
                    "dimensions": 1536,
                },
            ],
        },
    },
    "merges": {
        "partition_key": "/pk",
        "default_ttl": TTL_DISABLED,
        "unique_key_policy": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/*"},
            ],
            "excludedPaths": [
                {"path": "/originalStates/*"},
                {"path": "/_etag/?"},
            ],
        },
        "vector_embedding_policy": None,
    },
}


async def setup_containers(database: DatabaseProxy) -> dict[str, str]:
    """
    Create all required containers with indexing policies.

    Args:
        database: Cosmos DB database proxy.

    Returns:
        Dictionary mapping container names to their creation status.
    """
    results: dict[str, str] = {}

    for container_name, config in CONTAINERS.items():
        try:
            logger.info("Creating container: %s", container_name)
            create_kwargs: dict[str, Any] = {
                "id": container_name,
                "partition_key": PartitionKey(path=str(config["partition_key"])),
                "indexing_policy": config["indexing_policy"],
                "default_ttl": config["default_ttl"],
            }
            if config.get("unique_key_policy"):
                create_kwargs["unique_key_policy"] = config["unique_key_policy"]
            if config.get("vector_embedding_policy"):
                create_kwargs["vector_embedding_policy"] = config["vector_embedding_policy"]
            await database.create_container(**create_kwargs)
            results[container_name] = "created"
            logger.info("Container %s created successfully", container_name)
        except CosmosResourceExistsError:
            results[container_name] = "exists"
            logger.info("Container %s already exists", container_name)
        except Exception:
            logger.exception("Failed to create container %s", container_name)
            results[container_name] = "error"
            raise

    return results


async def ensure_database_setup(database: DatabaseProxy) -> None:
    """
    Ensure all containers exist with proper configuration.

    This is called during application startup.

    Args:
        database: Cosmos DB database proxy.
    """
    logger.info("Ensuring database setup...")
    results = await setup_containers(database)

    created = sum(1 for status in results.values() if status == "created")
    existing = sum(1 for status in results.values() if status == "exists")

    logger.info(
        "Database setup complete: %d containers created, %d already existed",
        created,
        existing,
    )


async def _run_standalone() -> None:
    """Run database + container setup as a standalone provisioning step."""
    from config import get_settings  # noqa: PLC0415

    settings = get_settings()

    print("=" * 60)
    print("Cosmos DB Setup")
    print("=" * 60)
    print(f"Endpoint: {settings.cosmos_endpoint}")
    print(f"Database: {settings.cosmos_database}")
    print()

    credential: Any
    if settings.cosmos_use_aad:
        from azure.identity.aio import DefaultAzureCredential  # noqa: PLC0415

        credential = DefaultAzureCredential()
        print("Auth: Microsoft Entra ID (AAD)")
    else:
        if not settings.cosmos_key:
            msg = (
                "COSMOS_KEY is required for setup. "
                "Set the environment variable or use COSMOS_USE_AAD=true."
            )
            raise RuntimeError(msg)
        credential = settings.cosmos_key.get_secret_value()
        print("Auth: Account key")

    client = CosmosClient(
        url=settings.cosmos_endpoint,
        credential=credential,
        connection_verify=settings.cosmos_ssl_verify,
    )

    try:
        # Create database if not exists
        try:
            print(f"Creating database '{settings.cosmos_database}'...")
            await client.create_database_if_not_exists(id=settings.cosmos_database)
            print(f"  Database '{settings.cosmos_database}' ready")
        except CosmosHttpResponseError as e:
            if e.status_code == 403:
                # AAD data-plane roles can't create databases; assume it exists
                print("  Database creation skipped (no control-plane permission)")
                print(f"  Assuming database '{settings.cosmos_database}' already exists")
            else:
                raise

        database = client.get_database_client(settings.cosmos_database)

        # Create containers
        print()
        results = await setup_containers(database)

        print()
        print("=" * 60)
        for name, status in results.items():
            print(f"  {name}: {status}")
        print("=" * 60)
        print("Setup complete")

        if any(s == "error" for s in results.values()):
            sys.exit(1)
    finally:
        await client.close()
        if settings.cosmos_use_aad and hasattr(credential, "close"):
            await credential.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    asyncio.run(_run_standalone())
