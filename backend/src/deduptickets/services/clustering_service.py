"""
Clustering service for duplicate ticket detection.

Implements real-time clustering with:
- Exact field matching (transactionId, merchant, category)
- Time window matching (tickets within configurable window)
- Text similarity (TF-IDF + cosine, configurable threshold)
- Confidence assignment (High/Medium/Low)

Constitution Compliance:
- Principle VIII: Async-first for all operations
- NFR: Clustering completes within 30 seconds
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from deduptickets.config import get_settings
from deduptickets.lib.similarity import TextSimilarityCalculator, quick_similarity
from deduptickets.models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
    ConfidenceLevel,
    ExactMatch,
    MatchingSignals,
    TextSimilarity,
)

if TYPE_CHECKING:
    from deduptickets.models.ticket import Ticket
    from deduptickets.repositories.cluster import ClusterRepository
    from deduptickets.repositories.ticket import TicketRepository

logger = logging.getLogger(__name__)


class ClusteringConfig:
    """Configuration for clustering behavior."""

    def __init__(
        self,
        *,
        similarity_threshold: float = 0.7,
        time_window_hours: int = 1,
        min_cluster_size: int = 2,
        exact_match_fields: list[str] | None = None,
    ) -> None:
        """
        Initialize clustering configuration.

        Args:
            similarity_threshold: Minimum text similarity (0.0-1.0).
            time_window_hours: Hours within which tickets are considered related.
            min_cluster_size: Minimum tickets to form a cluster.
            exact_match_fields: Fields that must match exactly.
        """
        self.similarity_threshold = similarity_threshold
        self.time_window_hours = time_window_hours
        self.min_cluster_size = min_cluster_size
        self.exact_match_fields = exact_match_fields or [
            "category",
            "severity",
            "channel",
        ]


def calculate_confidence_score(
    *,
    exact_field_matches: int,
    total_exact_fields: int,
    text_similarity: float,
    time_proximity: float,
) -> float:
    """
    Calculate overall confidence score for a cluster match.

    Weights:
    - Exact field matches: 40%
    - Text similarity: 40%
    - Time proximity: 20%

    Args:
        exact_field_matches: Number of fields that matched exactly.
        total_exact_fields: Total fields checked for exact match.
        text_similarity: Text similarity score (0.0-1.0).
        time_proximity: Time proximity score (0.0-1.0).

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    field_score = exact_field_matches / total_exact_fields if total_exact_fields > 0 else 0

    return (field_score * 0.4) + (text_similarity * 0.4) + (time_proximity * 0.2)


def calculate_time_proximity(
    time1: datetime,
    time2: datetime,
    window_hours: int,
) -> float:
    """
    Calculate time proximity score.

    Returns 1.0 if times are identical, decreasing linearly to 0.0 at window edge.

    Args:
        time1: First timestamp.
        time2: Second timestamp.
        window_hours: Maximum window in hours.

    Returns:
        Proximity score between 0.0 and 1.0.
    """
    diff = abs((time1 - time2).total_seconds())
    max_diff = window_hours * 3600

    if diff >= max_diff:
        return 0.0

    return 1.0 - (diff / max_diff)


class ClusteringService:
    """
    Service for detecting and managing duplicate ticket clusters.

    Provides real-time clustering when new tickets are ingested,
    using a combination of exact field matching and text similarity.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        cluster_repo: ClusterRepository,
        config: ClusteringConfig | None = None,
    ) -> None:
        """
        Initialize the clustering service.

        Args:
            ticket_repo: Repository for ticket operations.
            cluster_repo: Repository for cluster operations.
            config: Optional clustering configuration.
        """
        self._ticket_repo = ticket_repo
        self._cluster_repo = cluster_repo
        self._config = config or self._default_config()
        self._similarity_calc = TextSimilarityCalculator()

    def _default_config(self) -> ClusteringConfig:
        """Get default configuration from settings."""
        settings = get_settings()
        return ClusteringConfig(
            similarity_threshold=settings.similarity_threshold,
            time_window_hours=settings.clustering_time_window_hours,
        )

    async def find_or_create_cluster(
        self,
        ticket: Ticket,
        partition_key: str,
    ) -> Cluster | None:
        """
        Find an existing cluster for a ticket or create a new one.

        This is the main entry point called when a new ticket is ingested.

        Args:
            ticket: The newly ingested ticket.
            partition_key: Partition key for the ticket.

        Returns:
            Cluster if ticket was assigned to one, None otherwise.
        """
        logger.info("Finding cluster for ticket %s", ticket.id)

        # Step 1: Find candidate tickets with matching fields
        candidates = await self._find_candidates(ticket, partition_key)

        if not candidates:
            logger.debug("No candidate tickets found for %s", ticket.id)
            return None

        logger.debug("Found %d candidate tickets for %s", len(candidates), ticket.id)

        # Step 2: Score candidates and find best matches
        matches = await self._score_candidates(ticket, candidates)

        if not matches:
            logger.debug("No matches above threshold for %s", ticket.id)
            return None

        # Step 3: Check if any matched ticket is already in a cluster
        existing_cluster = await self._find_existing_cluster(matches, partition_key)

        if existing_cluster:
            # Add this ticket to the existing cluster
            return await self._add_to_cluster(ticket, existing_cluster, partition_key)

        # Step 4: Create a new cluster with the best match
        if len(matches) >= self._config.min_cluster_size - 1:
            return await self._create_cluster(ticket, matches, partition_key)

        return None

    async def _find_candidates(
        self,
        ticket: Ticket,
        partition_key: str,
    ) -> list[Ticket]:
        """
        Find candidate tickets for clustering.

        Candidates must:
        - Be in the same partition (region/month)
        - Match at least one exact field
        - Be within the time window
        - Not already be merged
        """
        # Query for similar tickets
        candidates = await self._ticket_repo.find_similar_tickets(
            category=ticket.category,
            channel=ticket.channel,
            severity=ticket.severity,
            partition_key=partition_key,
            exclude_ids=[ticket.id],
            limit=50,
        )

        # Filter by time window
        window_start = ticket.created_at - timedelta(hours=self._config.time_window_hours)
        window_end = ticket.created_at + timedelta(hours=self._config.time_window_hours)

        return [c for c in candidates if window_start <= c.created_at <= window_end]

    async def _score_candidates(
        self,
        ticket: Ticket,
        candidates: list[Ticket],
    ) -> list[tuple[Ticket, float, list[str]]]:
        """
        Score candidates based on similarity.

        Returns tickets with scores above threshold, sorted by score.
        """
        results: list[tuple[Ticket, float, list[str]]] = []

        # Combine summary and description for text comparison
        ticket_text = f"{ticket.summary} {ticket.description or ''}"

        for candidate in candidates:
            # Calculate exact field matches
            matching_fields: list[str] = []

            for field in self._config.exact_match_fields:
                ticket_value = getattr(ticket, field, None)
                candidate_value = getattr(candidate, field, None)

                if ticket_value and ticket_value == candidate_value:
                    matching_fields.append(field)

            # Calculate text similarity
            candidate_text = f"{candidate.summary} {candidate.description or ''}"
            text_sim = quick_similarity(ticket_text, candidate_text)

            # Calculate time proximity
            time_prox = calculate_time_proximity(
                ticket.created_at,
                candidate.created_at,
                self._config.time_window_hours,
            )

            # Calculate overall confidence
            confidence = calculate_confidence_score(
                exact_field_matches=len(matching_fields),
                total_exact_fields=len(self._config.exact_match_fields),
                text_similarity=text_sim,
                time_proximity=time_prox,
            )

            # Check if above threshold
            if confidence >= self._config.similarity_threshold:
                results.append((candidate, confidence, matching_fields))

        # Sort by confidence descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def _find_existing_cluster(
        self,
        matches: list[tuple[Ticket, float, list[str]]],
        partition_key: str,
    ) -> Cluster | None:
        """Find if any matched ticket is already in a pending cluster."""
        for ticket, _, _ in matches:
            if ticket.cluster_id:
                cluster = await self._cluster_repo.get_by_id(
                    ticket.cluster_id,
                    partition_key,
                )
                if cluster and cluster.status == ClusterStatus.PENDING:
                    return cluster
        return None

    async def _add_to_cluster(
        self,
        ticket: Ticket,
        cluster: Cluster,
        partition_key: str,
    ) -> Cluster:
        """Add a ticket to an existing cluster."""
        logger.info("Adding ticket %s to cluster %s", ticket.id, cluster.id)

        # Update ticket with cluster ID
        await self._ticket_repo.assign_to_cluster(
            ticket.id,
            cluster.id,
            partition_key,
        )

        # Update cluster with new ticket
        updated_cluster = await self._cluster_repo.add_ticket(
            cluster.id,
            ticket.id,
            partition_key,
        )

        return updated_cluster or cluster

    async def _create_cluster(
        self,
        ticket: Ticket,
        matches: list[tuple[Ticket, float, list[str]]],
        partition_key: str,
    ) -> Cluster:
        """Create a new cluster from ticket matches."""
        # Use the highest scoring match for cluster properties
        best_match, best_score, matching_fields = matches[0]

        # Collect all ticket members
        members = [
            ClusterMember(ticket_id=ticket.id, ticket_number=ticket.ticket_number),
            ClusterMember(ticket_id=best_match.id, ticket_number=best_match.ticket_number),
        ]

        # Add additional matches if they exist
        for match_ticket, score, _ in matches[1:]:
            if score >= self._config.similarity_threshold:
                members.append(
                    ClusterMember(
                        ticket_id=match_ticket.id,
                        ticket_number=match_ticket.ticket_number,
                    )
                )

        # Determine confidence level from score
        if best_score >= 0.9:
            confidence = ConfidenceLevel.HIGH
        elif best_score >= 0.7:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # Build matching signals
        exact_matches = [
            ExactMatch(field=f, value=str(getattr(ticket, f, ""))) for f in matching_fields
        ]
        matching_signals = MatchingSignals(
            exact_matches=exact_matches,
            text_similarity=TextSimilarity(score=best_score),
        )

        # Create cluster
        cluster = Cluster(
            id=uuid4(),
            pk=partition_key,
            members=members,
            ticket_count=len(members),
            confidence=confidence,
            summary=f"{ticket.category}: {ticket.summary[:100]}",
            status=ClusterStatus.PENDING,
            matching_signals=matching_signals,
        )

        logger.info(
            "Creating cluster %s with %d tickets (confidence: %s)",
            cluster.id,
            len(members),
            confidence,
        )

        # Save cluster
        created_cluster = await self._cluster_repo.create(cluster, partition_key)

        # Update all tickets with cluster ID
        for member in members:
            await self._ticket_repo.assign_to_cluster(member.ticket_id, cluster.id, partition_key)

        return created_cluster

    async def recluster_ticket(
        self,
        ticket_id: UUID,
        partition_key: str,
    ) -> Cluster | None:
        """
        Re-run clustering for an existing ticket.

        Useful after a ticket is removed from a cluster or dismissed.

        Args:
            ticket_id: Ticket to recluster.
            partition_key: Partition key.

        Returns:
            New cluster if found, None otherwise.
        """
        ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
        if not ticket:
            return None

        # Remove from current cluster if any
        if ticket.cluster_id:
            await self._cluster_repo.remove_ticket(
                ticket.cluster_id,
                ticket_id,
                partition_key,
            )
            await self._ticket_repo.remove_from_cluster(ticket_id, partition_key)

        # Find new cluster
        return await self.find_or_create_cluster(ticket, partition_key)

    async def dismiss_cluster(
        self,
        cluster_id: UUID,
        partition_key: str,
        *,
        dismissed_by: str,
        reason: str | None = None,
    ) -> Cluster | None:
        """
        Dismiss a cluster (mark as not duplicates).

        Args:
            cluster_id: Cluster to dismiss.
            partition_key: Partition key.
            dismissed_by: User dismissing the cluster.
            reason: Optional reason for dismissal.

        Returns:
            Updated cluster.
        """
        logger.info("Dismissing cluster %s by %s", cluster_id, dismissed_by)

        return await self._cluster_repo.update_status(
            cluster_id,
            ClusterStatus.DISMISSED,
            partition_key,
            dismissed_by=dismissed_by,
            dismissal_reason=reason,
        )

    async def remove_ticket_from_cluster(
        self,
        cluster_id: UUID,
        ticket_id: UUID,
        partition_key: str,
    ) -> Cluster | None:
        """
        Remove a single ticket from a cluster.

        If cluster becomes too small, it may be auto-dismissed.

        Args:
            cluster_id: Cluster ID.
            ticket_id: Ticket to remove.
            partition_key: Partition key.

        Returns:
            Updated cluster.
        """
        logger.info("Removing ticket %s from cluster %s", ticket_id, cluster_id)

        # Remove ticket from cluster
        updated_cluster = await self._cluster_repo.remove_ticket(
            cluster_id,
            ticket_id,
            partition_key,
        )

        # Update ticket
        await self._ticket_repo.remove_from_cluster(ticket_id, partition_key)

        # Auto-dismiss if only one ticket remains
        if updated_cluster and updated_cluster.ticket_count < self._config.min_cluster_size:
            logger.info("Cluster %s too small, auto-dismissing", cluster_id)
            return await self._cluster_repo.update_status(
                cluster_id,
                ClusterStatus.DISMISSED,
                partition_key,
                dismissal_reason="Cluster became too small",
            )

        return updated_cluster
