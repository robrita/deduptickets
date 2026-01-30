"""
Cosmos DB container setup script with indexing policies.

Creates all required containers with proper partition keys and indexing policies
as defined in data-model.md.

Constitution Compliance:
- Principle V: Performance Budgets - Composite indexes for common query patterns
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azure.cosmos import PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError

if TYPE_CHECKING:
    from azure.cosmos.aio import DatabaseProxy

logger = logging.getLogger(__name__)

# Container configurations per data-model.md
CONTAINERS = {
    "tickets": {
        "partition_key": "/pk",
        "default_ttl": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/status/*"},
                {"path": "/category/*"},
                {"path": "/channel/*"},
                {"path": "/transactionId/*"},
                {"path": "/merchant/*"},
                {"path": "/createdAt/*"},
                {"path": "/region/*"},
            ],
            "excludedPaths": [
                {"path": "/description/*"},
                {"path": "/name/*"},
                {"path": "/mobileNumber/*"},
                {"path": "/email/*"},
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
        },
    },
    "clusters": {
        "partition_key": "/pk",
        "default_ttl": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/status/*"},
                {"path": "/confidence/*"},
                {"path": "/createdAt/*"},
                {"path": "/primaryTicketId/*"},
            ],
            "excludedPaths": [
                {"path": "/matchingSignals/*"},
                {"path": "/members/*"},
                {"path": "/_etag/?"},
            ],
            "compositeIndexes": [
                [
                    {"path": "/status", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
            ],
        },
    },
    "merges": {
        "partition_key": "/pk",
        "default_ttl": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/status/*"},
                {"path": "/clusterId/*"},
                {"path": "/performedAt/*"},
            ],
            "excludedPaths": [
                {"path": "/originalStates/*"},
                {"path": "/_etag/?"},
            ],
        },
    },
    "audit": {
        "partition_key": "/pk",
        "default_ttl": 7776000,  # 90 days in seconds
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/actionType/*"},
                {"path": "/actorId/*"},
                {"path": "/resourceType/*"},
                {"path": "/resourceId/*"},
                {"path": "/createdAt/*"},
            ],
            "excludedPaths": [
                {"path": "/metadata/*"},
                {"path": "/userAgent/*"},
                {"path": "/_etag/?"},
            ],
            "compositeIndexes": [
                [
                    {"path": "/resourceType", "order": "ascending"},
                    {"path": "/resourceId", "order": "ascending"},
                    {"path": "/createdAt", "order": "descending"},
                ],
            ],
        },
    },
    "spikes": {
        "partition_key": "/pk",
        "default_ttl": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/status/*"},
                {"path": "/severity/*"},
                {"path": "/fieldName/*"},
                {"path": "/detectedAt/*"},
            ],
            "excludedPaths": [
                {"path": "/affectedClusterIds/*"},
                {"path": "/_etag/?"},
            ],
        },
    },
    "baselines": {
        "partition_key": "/pk",
        "default_ttl": None,
        "indexing_policy": {
            "indexingMode": "consistent",
            "automatic": True,
            "includedPaths": [
                {"path": "/fieldName/*"},
                {"path": "/fieldValue/*"},
                {"path": "/hourOfDay/*"},
                {"path": "/dayOfWeek/*"},
            ],
            "excludedPaths": [
                {"path": "/_etag/?"},
            ],
        },
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
            await database.create_container(
                id=container_name,
                partition_key=PartitionKey(path=config["partition_key"]),
                indexing_policy=config["indexing_policy"],
                default_ttl=config["default_ttl"],
            )
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
