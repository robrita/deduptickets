"""
Utility libraries for deduptickets.

Contains reusable utilities for embedding generation, etc.
"""

from lib.embedding import EmbeddingService, build_dedup_text

__all__ = [
    "EmbeddingService",
    "build_dedup_text",
]
