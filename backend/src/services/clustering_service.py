"""
Cluster-first dedup service for duplicate ticket detection.

Implements hybrid pipeline:
- Embed ticket text via Azure OpenAI
- Search clusters (not tickets) via Cosmos DB VectorDistance()
- Multi-signal scoring with configurable weights (semantic, subcategory, category, time)
- Three-tier decision: auto / review / new_cluster (configurable thresholds)
- ETag-safe incremental centroid updates

"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from azure.cosmos.exceptions import CosmosHttpResponseError

from config import get_settings
from models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
)

if TYPE_CHECKING:
    from lib.embedding import EmbeddingService
    from models.ticket import Ticket
    from repositories.cluster import ClusterRepository
    from repositories.ticket import TicketRepository

logger = logging.getLogger(__name__)

# Maximum retries for ETag conflict during centroid update
_MAX_ETAG_RETRIES = 3

_DECISION_REASON_NO_CANDIDATES = "no_candidates"
_DECISION_REASON_ABOVE_AUTO_THRESHOLD = "above_auto_threshold"
_DECISION_REASON_REVIEW_BAND = "review_band"
_DECISION_REASON_BELOW_REVIEW_THRESHOLD = "below_review_threshold"


def _compute_confidence_score(
    *,
    semantic_score: float,
    subcategory_match: bool,
    category_match: bool,
    time_proximity: float,
    w_semantic: float = 0.85,
    w_subcategory: float = 0.10,
    w_category: float = 0.03,
    w_time: float = 0.02,
) -> float:
    """
    Compute multi-signal confidence score.

    Formula: w_semantic*semantic + w_subcategory*subcategory + w_category*category + w_time*time
    Weights are configurable via settings.
    """
    return (
        w_semantic * semantic_score
        + w_subcategory * (1.0 if subcategory_match else 0.0)
        + w_category * (1.0 if category_match else 0.0)
        + w_time * time_proximity
    )


def _compute_time_proximity(
    ticket_created: datetime,
    cluster_updated: datetime,
    window_days: int,
) -> float:
    """
    Compute time proximity score (0.0-1.0).

    Returns 1.0 when timestamps are identical, linearly decaying to 0.0
    at the edge of the window.
    """
    # Normalize both to aware UTC for safe subtraction
    if ticket_created.tzinfo is None:
        ticket_created = ticket_created.replace(tzinfo=UTC)
    if cluster_updated.tzinfo is None:
        cluster_updated = cluster_updated.replace(tzinfo=UTC)
    diff = abs((ticket_created - cluster_updated).total_seconds())
    max_diff = window_days * 86400  # days to seconds

    if diff >= max_diff:
        return 0.0
    return 1.0 - (diff / max_diff)


def _generate_partition_keys(reference: datetime, months: int) -> list[str]:
    """
    Generate partition keys for current + previous N-1 months.

    Args:
        reference: Reference timestamp (typically now or ticket.created_at).
        months: Total number of months to cover.

    Returns:
        List of YYYY-MM strings, newest first.
    """
    keys: list[str] = []
    dt = reference.replace(day=1)
    for _ in range(months):
        keys.append(dt.strftime("%Y-%m"))
        dt = (dt - timedelta(days=1)).replace(day=1)
    return keys


def _update_centroid(
    old_centroid: list[float],
    new_vector: list[float],
    n: int,
) -> list[float]:
    """
    Incrementally update centroid vector.

    new_centroid[i] = (old_centroid[i] * n + new_vector[i]) / (n + 1)

    Args:
        old_centroid: Current centroid.
        new_vector: New ticket's embedding.
        n: Number of vectors already in the centroid (ticket_count).

    Returns:
        Updated centroid vector.
    """
    return [(old * n + new) / (n + 1) for old, new in zip(old_centroid, new_vector, strict=True)]


class ClusteringService:
    """
    Cluster-first dedup service.

    Searches existing clusters via vector similarity, scores candidates
    with a multi-signal formula, applies three-tier decisions, and
    manages cluster lifecycle with ETag-safe centroid updates.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        cluster_repo: ClusterRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        self._ticket_repo = ticket_repo
        self._cluster_repo = cluster_repo
        self._embedding_service = embedding_service

    async def find_or_create_cluster(
        self,
        ticket: Ticket,
        partition_key: str,
    ) -> tuple[Cluster, dict[str, Any]]:
        """
        Find an existing cluster for a ticket or create a new one.

        This is the main entry point called when a new ticket is ingested.
        The ticket must already have content_vector and dedup_text set.

        Args:
            ticket: Ticket with embedding already generated.
            partition_key: Partition key for the ticket.

        Returns:
            Tuple of (cluster, dedup_metadata) where dedup_metadata contains
            decision, score, signals, and optional explain_tickets.
        """
        settings = get_settings()
        query_vector = ticket.content_vector
        if not query_vector:
            msg = "Ticket must have content_vector set before clustering"
            raise ValueError(msg)

        logger.info("Finding cluster for ticket %s", ticket.id)

        # Generate partition keys for search scope
        pk_list = _generate_partition_keys(
            ticket.created_at,
            settings.cluster_search_months,
        )

        # Time window lower bound
        min_updated = (ticket.created_at - timedelta(days=settings.dedup_window_days)).isoformat()

        # Step 1: Vector search for cluster candidates (excludes full clusters)
        candidates = await self._cluster_repo.find_cluster_candidates(
            customer_id=ticket.customer_id,
            min_updated_at=min_updated,
            query_vector=query_vector,
            top_k=settings.cluster_top_k,
            partition_keys=pk_list,
            filter_by_customer=settings.dedup_filter_by_customer,
            max_members=settings.cluster_max_members,
        )

        if not candidates:
            logger.info(
                "[DEDUP] %s → NEW_CLUSTER | reason: %s | candidates: 0"
                " | thresholds: auto=%.2f  review=%.2f",
                ticket.id,
                _DECISION_REASON_NO_CANDIDATES,
                settings.cluster_auto_threshold,
                settings.cluster_review_threshold,
            )
            return await self._create_new_cluster(
                ticket,
                partition_key,
                query_vector,
                decision_context={
                    "decisionReason": _DECISION_REASON_NO_CANDIDATES,
                    "candidateCount": 0,
                    "autoThreshold": settings.cluster_auto_threshold,
                    "reviewThreshold": settings.cluster_review_threshold,
                },
            )

        # Step 2: Score and rank all candidates
        ranked = self._score_candidates(ticket, candidates, settings.dedup_window_days)

        if not ranked:
            logger.debug("No candidates above threshold for %s — creating new", ticket.id)
            return await self._create_new_cluster(ticket, partition_key, query_vector)

        # Step 3: Try candidates in ranked order (handles race condition
        # where a cluster fills between query and add_member)
        last_new_cluster_entry = None
        for candidate, confidence, decision, decision_reason, signal_breakdown in ranked:
            if decision == "new_cluster":
                # Keep the best "new_cluster" entry for context if all fail
                if last_new_cluster_entry is None:
                    last_new_cluster_entry = (
                        candidate,
                        confidence,
                        decision_reason,
                        signal_breakdown,
                    )
                continue

            # auto or review — try to add to this cluster
            try:
                cluster = await self._add_to_existing_cluster(
                    ticket,
                    candidate,
                    partition_key,
                    query_vector,
                    confidence=confidence,
                    max_members=settings.cluster_max_members,
                )
            except ValueError:
                logger.warning(
                    "Cluster %s at capacity during add (race condition), trying next candidate",
                    candidate.get("id"),
                )
                continue

            dedup_meta: dict[str, Any] = {
                "decision": decision,
                "decisionReason": decision_reason,
                "confidenceScore": round(confidence, 4),
                "matchedClusterId": str(cluster.id),
                "semanticScore": round(candidate.get("similarityScore", 0), 4),
                "signals": {
                    "subcategoryMatch": (
                        ticket.subcategory is not None
                        and ticket.subcategory == candidate.get("subcategory")
                    ),
                    "categoryMatch": ticket.category == candidate.get("category"),
                    "timeProximity": round(signal_breakdown["timeProximity"], 4),
                },
            }

            return cluster, dedup_meta

        # All eligible candidates failed (full or below threshold) — create new
        decision_context: dict[str, Any] | None = None
        if last_new_cluster_entry:
            cand, score, reason, signals = last_new_cluster_entry
            decision_context = {
                "decisionReason": reason,
                "candidateCount": len(candidates),
                "autoThreshold": settings.cluster_auto_threshold,
                "reviewThreshold": settings.cluster_review_threshold,
                "bestCandidateId": cand.get("id"),
                "bestScore": score,
                "semanticScore": signals["semanticScore"],
                "signals": {
                    "subcategoryMatch": signals["subcategoryMatch"],
                    "categoryMatch": signals["categoryMatch"],
                    "timeProximity": signals["timeProximity"],
                },
            }

        return await self._create_new_cluster(
            ticket,
            partition_key,
            query_vector,
            decision_context=decision_context,
        )

    def _score_candidates(
        self,
        ticket: Ticket,
        candidates: list[dict[str, Any]],
        window_days: int,
    ) -> list[tuple[dict[str, Any], float, str, str, dict[str, Any]]]:
        """
        Score all candidates and return a ranked list with decisions.

        Returns:
            List of (candidate_dict, confidence_score, decision,
            decision_reason, signal_breakdown) sorted by confidence descending.
        """
        settings = get_settings()
        scored: list[tuple[dict[str, Any], float, str, str, dict[str, Any]]] = []

        for cand in candidates:
            semantic = cand.get("similarityScore", 0.0)

            subcategory_match = ticket.subcategory is not None and ticket.subcategory == cand.get(
                "subcategory"
            )
            category_match = ticket.category == cand.get("category")

            # Parse cluster updatedAt for time proximity
            updated_str = cand.get("updatedAt", "")
            try:
                cluster_updated = datetime.fromisoformat(updated_str)
            except (ValueError, TypeError):
                cluster_updated = ticket.created_at

            time_prox = _compute_time_proximity(
                ticket.created_at,
                cluster_updated,
                window_days,
            )

            score = _compute_confidence_score(
                semantic_score=semantic,
                subcategory_match=subcategory_match,
                category_match=category_match,
                time_proximity=time_prox,
                w_semantic=settings.dedup_weight_semantic,
                w_subcategory=settings.dedup_weight_subcategory,
                w_category=settings.dedup_weight_category,
                w_time=settings.dedup_weight_time,
            )

            logger.debug(
                "Candidate cluster %s: semantic=%.4f subcategory_match=%s "
                "category_match=%s time_proximity=%.4f => confidence=%.4f",
                cand.get("id"),
                semantic,
                subcategory_match,
                category_match,
                time_prox,
                score,
            )

            # Three-tier decision
            if score >= settings.cluster_auto_threshold:
                decision = "auto"
                decision_reason = _DECISION_REASON_ABOVE_AUTO_THRESHOLD
            elif score >= settings.cluster_review_threshold:
                decision = "review"
                decision_reason = _DECISION_REASON_REVIEW_BAND
            else:
                decision = "new_cluster"
                decision_reason = _DECISION_REASON_BELOW_REVIEW_THRESHOLD

            signal_breakdown = {
                "semanticScore": semantic,
                "subcategoryMatch": subcategory_match,
                "categoryMatch": category_match,
                "timeProximity": time_prox,
            }

            scored.append((cand, score, decision, decision_reason, signal_breakdown))

        # Sort by confidence descending
        scored.sort(key=lambda x: x[1], reverse=True)

        if scored:
            best_cand, best_score, best_decision, best_reason, best_signals = scored[0]
            logger.info(
                "[DEDUP] %s → %s | reason: %s | candidates: %d"
                " | best_match: cluster=%s  conf=%.4f"
                " | signals: semantic=%.4f  subcategory=%s  category=%s  time=%.4f"
                " | thresholds: auto=%.2f  review=%.2f",
                ticket.id,
                best_decision.upper(),
                best_reason,
                len(candidates),
                best_cand.get("id"),
                best_score,
                best_signals["semanticScore"],
                best_signals["subcategoryMatch"],
                best_signals["categoryMatch"],
                best_signals["timeProximity"],
                settings.cluster_auto_threshold,
                settings.cluster_review_threshold,
            )

        return scored

    async def _create_new_cluster(
        self,
        ticket: Ticket,
        partition_key: str,
        embedding: list[float],
        decision_context: dict[str, Any] | None = None,
    ) -> tuple[Cluster, dict[str, Any]]:
        """Create a new CANDIDATE cluster with a single ticket."""
        member = ClusterMember(
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            summary=ticket.summary,
            category=ticket.category,
            subcategory=ticket.subcategory,
            created_at=ticket.created_at,
            confidence_score=None,
        )

        is_open = ticket.status.value in get_settings().dedup_open_statuses

        cluster = Cluster(
            id=uuid4(),
            pk=partition_key,
            members=[member],
            ticket_count=1,
            summary=f"{ticket.category}: {ticket.summary[:100]}",
            status=ClusterStatus.CANDIDATE,
            centroid_vector=embedding,
            customer_id=ticket.customer_id,
            category=ticket.category,
            subcategory=ticket.subcategory,
            open_count=1 if is_open else 0,
            representative_ticket_id=ticket.id,
        )

        logger.info("Creating CANDIDATE cluster %s for ticket %s", cluster.id, ticket.id)
        created = await self._cluster_repo.create(cluster, partition_key)

        # Assign ticket to cluster
        await self._ticket_repo.assign_to_cluster(ticket.id, created.id, partition_key)

        dedup_meta: dict[str, Any] = {
            "decision": "new_cluster",
            "decisionReason": _DECISION_REASON_NO_CANDIDATES,
            "confidenceScore": 0.0,
            "matchedClusterId": str(created.id),
            "semanticScore": 0.0,
            "signals": {},
        }

        if decision_context:
            dedup_meta["decisionReason"] = decision_context.get(
                "decisionReason",
                _DECISION_REASON_NO_CANDIDATES,
            )
            dedup_meta["confidenceScore"] = round(decision_context.get("bestScore", 0.0), 4)
            dedup_meta["semanticScore"] = round(decision_context.get("semanticScore", 0.0), 4)
            dedup_meta["signals"] = decision_context.get("signals", {})

        return created, dedup_meta

    async def _add_to_existing_cluster(
        self,
        ticket: Ticket,
        candidate: dict[str, Any],
        ticket_partition_key: str,
        embedding: list[float],
        *,
        confidence: float,
        max_members: int = 100,
    ) -> Cluster:
        """
        Add ticket to an existing cluster with ETag-safe centroid update.

        If the cluster was CANDIDATE (single member), promote to PENDING.

        Raises:
            ValueError: If cluster is at capacity (race condition).
        """
        cluster_id = UUID(candidate["id"])
        cluster_pk = candidate["pk"]

        cluster = await self._cluster_repo.get_by_id(cluster_id, cluster_pk)
        if not cluster:
            msg = f"Cluster {cluster_id} not found during add"
            raise ValueError(msg)

        # Update centroid with ETag retry loop
        for attempt in range(_MAX_ETAG_RETRIES):
            # Add member
            cluster.add_member(
                ticket.id,
                ticket.ticket_number,
                summary=ticket.summary,
                category=ticket.category,
                subcategory=ticket.subcategory,
                created_at=ticket.created_at,
                confidence_score=round(confidence, 4),
                max_members=max_members,
            )

            # Incremental centroid update
            if cluster.centroid_vector:
                cluster.centroid_vector = _update_centroid(
                    cluster.centroid_vector,
                    embedding,
                    cluster.ticket_count - 1,  # n = count before adding this ticket
                )
            else:
                cluster.centroid_vector = embedding

            # Update open count
            is_open = ticket.status.value in get_settings().dedup_open_statuses
            if is_open:
                cluster.open_count += 1

            # Promote CANDIDATE → PENDING when second ticket joins
            if cluster.status == ClusterStatus.CANDIDATE:
                cluster.status = ClusterStatus.PENDING
                logger.info("Promoting cluster %s from CANDIDATE to PENDING", cluster_id)

            try:
                cluster = await self._cluster_repo.update_cluster_with_etag(
                    cluster,
                )
                break
            except CosmosHttpResponseError as exc:
                if exc.status_code == 412 and attempt < _MAX_ETAG_RETRIES - 1:
                    logger.warning(
                        "ETag conflict on cluster %s (attempt %d), retrying",
                        cluster_id,
                        attempt + 1,
                    )
                    # Re-fetch to get fresh ETag
                    cluster = await self._cluster_repo.get_by_id(cluster_id, cluster_pk)
                    if not cluster:
                        msg = f"Cluster {cluster_id} disappeared during retry"
                        raise ValueError(msg) from exc
                else:
                    raise

        # Assign ticket to cluster
        await self._ticket_repo.assign_to_cluster(ticket.id, cluster.id, ticket_partition_key)

        return cluster

    async def dismiss_cluster(
        self,
        cluster_id: UUID,
        partition_key: str,
        *,
        dismissed_by: str,
        reason: str | None = None,
    ) -> Cluster:
        """
        Dismiss a cluster (mark as not duplicates).

        Args:
            cluster_id: Cluster to dismiss.
            partition_key: Partition key.
            dismissed_by: User dismissing the cluster.
            reason: Optional reason for dismissal.

        Returns:
            Updated cluster.

        Raises:
            ValueError: If cluster not found or already dismissed.
        """
        cluster = await self._cluster_repo.get_by_id(cluster_id, partition_key)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        if cluster.status == ClusterStatus.DISMISSED:
            raise ValueError("Cluster is already dismissed")

        logger.info("Dismissing cluster %s by %s", cluster_id, dismissed_by)

        updated = await self._cluster_repo.update_status(
            cluster_id,
            ClusterStatus.DISMISSED,
            partition_key,
            dismissed_by=dismissed_by,
            dismissal_reason=reason,
        )
        if not updated:
            msg = "Failed to update cluster"
            raise ValueError(msg)
        return updated

    async def remove_ticket_from_cluster(
        self,
        cluster_id: UUID,
        ticket_id: UUID,
        partition_key: str,
    ) -> Cluster:
        """
        Remove a single ticket from a cluster.

        If cluster goes to 1 member, demote to CANDIDATE.

        Args:
            cluster_id: Cluster ID.
            ticket_id: Ticket to remove.
            partition_key: Partition key.

        Returns:
            Updated cluster.

        Raises:
            ValueError: If cluster not found, ticket not in cluster,
                        or cluster is not PENDING/CANDIDATE.
        """
        cluster = await self._cluster_repo.get_by_id(cluster_id, partition_key)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        if ticket_id not in cluster.ticket_ids:
            raise ValueError(f"Ticket {ticket_id} is not in cluster {cluster_id}")

        if cluster.status not in (ClusterStatus.PENDING, ClusterStatus.CANDIDATE):
            raise ValueError(f"Cannot modify cluster with status {cluster.status.value}")

        logger.info("Removing ticket %s from cluster %s", ticket_id, cluster_id)

        # Remove ticket from cluster
        updated_cluster = await self._cluster_repo.remove_ticket(
            cluster_id,
            ticket_id,
            partition_key,
        )
        if not updated_cluster:
            msg = "Failed to remove ticket from cluster"
            raise ValueError(msg)

        # Update ticket
        await self._ticket_repo.remove_from_cluster(ticket_id, partition_key)

        # Demote to CANDIDATE if only 1 member remains
        if updated_cluster.ticket_count == 1:
            logger.info("Cluster %s down to 1 member, demoting to CANDIDATE", cluster_id)
            demoted = await self._cluster_repo.update_status(
                cluster_id,
                ClusterStatus.CANDIDATE,
                partition_key,
            )
            return demoted or updated_cluster

        return updated_cluster
