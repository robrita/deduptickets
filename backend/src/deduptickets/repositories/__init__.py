"""
Repository layer for Cosmos DB operations.

Provides data access patterns with Cosmos DB best practices:
- Async operations throughout
- Proper partition key usage
- Generic base repository with common CRUD
- Entity-specific repositories with domain logic
"""

from deduptickets.repositories.audit import AuditRepository
from deduptickets.repositories.base import BaseRepository
from deduptickets.repositories.baseline import BaselineRepository
from deduptickets.repositories.cluster import ClusterRepository
from deduptickets.repositories.merge import MergeRepository
from deduptickets.repositories.spike import SpikeRepository
from deduptickets.repositories.ticket import TicketRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "BaselineRepository",
    "ClusterRepository",
    "MergeRepository",
    "SpikeRepository",
    "TicketRepository",
]
