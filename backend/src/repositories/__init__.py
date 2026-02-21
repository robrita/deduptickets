"""
Repository layer for Cosmos DB operations.

Provides data access patterns with Cosmos DB best practices:
- Async operations throughout
- Proper partition key usage
- Generic base repository with common CRUD
- Entity-specific repositories with domain logic
"""

from repositories.base import BaseRepository
from repositories.cluster import ClusterRepository
from repositories.merge import MergeRepository
from repositories.ticket import TicketRepository

__all__ = [
    "BaseRepository",
    "ClusterRepository",
    "MergeRepository",
    "TicketRepository",
]
