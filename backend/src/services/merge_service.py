"""
Merge service for duplicate ticket operations.

Implements:
- Merge cluster into canonical ticket
- Optimistic concurrency control
- Merge revert with conflict detection


Constitution Compliance:
- Principle VIII: Async-first
- FR-011/012/013: Revert capability with conflict detection
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from models.cluster import ClusterStatus
from models.merge_operation import MergeOperation, MergeStatus, TicketSnapshot

if TYPE_CHECKING:
    from repositories.cluster import ClusterRepository
    from repositories.merge import MergeRepository
    from repositories.ticket import TicketRepository


logger = logging.getLogger(__name__)


class MergeConflictError(Exception):
    """Raised when merge or revert has conflicts."""

    def __init__(self, message: str, conflicts: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.conflicts = conflicts or []


class MergeNotFoundError(Exception):
    """Raised when merge operation is not found."""

    pass


class MergeAlreadyRevertedError(Exception):
    """Raised when trying to revert an already reverted merge."""

    pass


class RevertWindowExpiredError(Exception):
    """Raised when the revert window has expired."""

    pass


class MergeService:
    """
    Service for merging and reverting duplicate tickets.

    Handles the complete lifecycle of merge operations including
    creating, validating, and reverting merges.
    """

    def __init__(
        self,
        ticket_repo: TicketRepository,
        cluster_repo: ClusterRepository,
        merge_repo: MergeRepository,
        *,
        revert_window_hours: int = 24,
    ) -> None:
        """
        Initialize the merge service.

        Args:
            ticket_repo: Repository for ticket operations.
            cluster_repo: Repository for cluster operations.
            merge_repo: Repository for merge operations.
            revert_window_hours: Hours within which a merge can be reverted.
        """
        self._ticket_repo = ticket_repo
        self._cluster_repo = cluster_repo
        self._merge_repo = merge_repo
        self._revert_window_hours = revert_window_hours

    async def merge_cluster(
        self,
        cluster_id: UUID,
        canonical_ticket_id: UUID,
        partition_key: str,
        *,
        merged_by: str,
    ) -> MergeOperation:
        """
        Merge a cluster into a canonical ticket.

        All tickets in the cluster except the canonical one will be
        marked as merged into the canonical ticket.

        Args:
            cluster_id: Cluster to merge.
            canonical_ticket_id: Ticket to keep as the primary.
            partition_key: Partition key.
            merged_by: User performing the merge.

        Returns:
            Created merge operation.

        Raises:
            ValueError: If cluster or ticket not found, or ticket not in cluster.
            MergeConflictError: If there's a concurrency conflict.
        """
        logger.info(
            "Merging cluster %s with canonical ticket %s by %s",
            cluster_id,
            canonical_ticket_id,
            merged_by,
        )

        # Validate cluster
        cluster = await self._cluster_repo.get_by_id(cluster_id, partition_key)
        if not cluster:
            raise ValueError(f"Cluster {cluster_id} not found")

        if cluster.status == ClusterStatus.CANDIDATE:
            raise ValueError("Cannot merge a CANDIDATE cluster (single-member)")

        if cluster.status != ClusterStatus.PENDING:
            raise ValueError(f"Cluster status is {cluster.status.value}, expected pending")

        # Validate canonical ticket is in cluster
        if canonical_ticket_id not in cluster.ticket_ids:
            raise ValueError("Canonical ticket is not in the cluster")

        # Get merged ticket IDs (all except canonical)
        merged_ticket_ids = [tid for tid in cluster.ticket_ids if tid != canonical_ticket_id]

        if not merged_ticket_ids:
            raise ValueError("No tickets to merge")

        # Capture original states for revert capability
        original_states = await self._capture_ticket_states(
            merged_ticket_ids,
            partition_key,
        )

        # Create merge operation
        now = datetime.now(UTC)
        merge = MergeOperation(
            id=uuid4(),
            cluster_id=cluster_id,
            primary_ticket_id=canonical_ticket_id,
            secondary_ticket_ids=merged_ticket_ids,
            performed_by=merged_by,
            performed_at=now,
            status=MergeStatus.COMPLETED,
            revert_deadline=now + timedelta(hours=self._revert_window_hours),
            original_states=original_states,
            pk=partition_key,
        )

        # Save merge operation
        created_merge = await self._merge_repo.create(merge, partition_key)

        # Update cluster status
        await self._cluster_repo.update_status(
            cluster_id,
            ClusterStatus.MERGED,
            partition_key,
        )

        # Update merged tickets to reference canonical and adjust open_count
        open_count_delta = 0
        for ticket_id in merged_ticket_ids:
            ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
            if ticket:
                if ticket.status.value in ("open", "pending"):
                    open_count_delta -= 1
                ticket.merged_into_id = canonical_ticket_id
                ticket.updated_at = now
                await self._ticket_repo.update(ticket, partition_key)

        # Decrement cluster open_count for merged tickets
        if open_count_delta:
            refreshed = await self._cluster_repo.get_by_id(cluster_id, partition_key)
            if refreshed:
                refreshed.open_count = max(0, refreshed.open_count + open_count_delta)
                await self._cluster_repo.update(refreshed, partition_key)

        logger.info(
            "Merge %s completed: %d tickets merged into %s",
            created_merge.id,
            len(merged_ticket_ids),
            canonical_ticket_id,
        )

        return created_merge

    async def _capture_ticket_states(
        self,
        ticket_ids: list[UUID],
        partition_key: str,
    ) -> list[TicketSnapshot]:
        """Capture current state of tickets for potential revert."""
        snapshots: list[TicketSnapshot] = []

        for ticket_id in ticket_ids:
            ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
            if ticket:
                snapshots.append(
                    TicketSnapshot(
                        ticket_id=ticket_id,
                        snapshot={
                            "clusterId": str(ticket.cluster_id) if ticket.cluster_id else None,
                            "mergedIntoId": (
                                str(ticket.merged_into_id) if ticket.merged_into_id else None
                            ),
                            "updatedAt": (
                                ticket.updated_at.isoformat() if ticket.updated_at else None
                            ),
                        },
                    )
                )

        return snapshots

    async def revert_merge(
        self,
        merge_id: UUID,
        partition_key: str,
        *,
        reverted_by: str,
        reason: str | None = None,
        force: bool = False,
    ) -> MergeOperation:
        """
        Revert a merge operation.

        Restores tickets to their pre-merge state.

        Args:
            merge_id: Merge operation to revert.
            partition_key: Partition key.
            reverted_by: User performing the revert.
            reason: Reason for revert.
            force: Force revert even with conflicts.

        Returns:
            Updated merge operation.

        Raises:
            MergeNotFoundError: If merge not found.
            MergeAlreadyRevertedError: If already reverted.
            RevertWindowExpiredError: If revert window expired.
            MergeConflictError: If conflicts detected and force=False.
        """
        logger.info("Reverting merge %s by %s", merge_id, reverted_by)

        # Get merge operation
        merge = await self._merge_repo.get_by_id(merge_id, partition_key)
        if not merge:
            raise MergeNotFoundError(f"Merge {merge_id} not found")

        # Check if already reverted
        if merge.status == MergeStatus.REVERTED:
            raise MergeAlreadyRevertedError("Merge is already reverted")

        # Check revert window
        now = datetime.now(UTC)
        revert_deadline = merge.revert_deadline
        if revert_deadline and revert_deadline.tzinfo is None:
            revert_deadline = revert_deadline.replace(tzinfo=UTC)
        if revert_deadline and now > revert_deadline:
            raise RevertWindowExpiredError("Revert window has expired")

        # Check for conflicts with subsequent merges
        conflicts = await self._check_revert_conflicts(merge, partition_key)
        if conflicts and not force:
            raise MergeConflictError(
                "Conflicts detected with subsequent merges",
                conflicts,
            )

        # Restore tickets to original state
        await self._restore_ticket_states(merge, partition_key)

        # Update merge status
        updated_merge = await self._merge_repo.update_status(
            merge_id,
            MergeStatus.REVERTED,
            partition_key,
            reverted_by=reverted_by,
            reverted_at=now,
            revert_reason=reason,
        )

        # Restore cluster to pending status and recalculate open_count
        await self._cluster_repo.update_status(
            merge.cluster_id,
            ClusterStatus.PENDING,
            partition_key,
        )

        # Increment open_count for reverted tickets that are open
        open_count_delta = 0
        for ticket_id in merge.secondary_ticket_ids:
            ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
            if ticket and ticket.status.value in ("open", "pending"):
                open_count_delta += 1

        if open_count_delta:
            refreshed = await self._cluster_repo.get_by_id(
                merge.cluster_id,
                partition_key,
            )
            if refreshed:
                refreshed.open_count += open_count_delta
                await self._cluster_repo.update(refreshed, partition_key)

        logger.info("Merge %s reverted successfully", merge_id)
        return updated_merge or merge

    async def _check_revert_conflicts(
        self,
        merge: MergeOperation,
        partition_key: str,
    ) -> list[dict[str, Any]]:
        """Check for conflicts that would prevent clean revert."""
        conflicts: list[dict[str, Any]] = []

        # Check for subsequent merges involving the canonical ticket
        subsequent_merges = await self._merge_repo.check_revert_conflicts(
            merge.id,
            partition_key,
        )

        for subsequent in subsequent_merges:
            conflicts.append(
                {
                    "type": "subsequent_merge",
                    "merge_id": str(subsequent.id),
                    "merged_at": subsequent.performed_at.isoformat(),
                }
            )

        # Check if any merged tickets have been modified
        for ticket_id in merge.secondary_ticket_ids:
            ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
            if ticket:
                original_state = merge.get_snapshot(ticket_id) or {}
                original_updated = original_state.get("updatedAt")

                if ticket.updated_at and original_updated:
                    original_dt = datetime.fromisoformat(original_updated)
                    # Normalize to aware UTC for safe comparison
                    if original_dt.tzinfo is None:
                        original_dt = original_dt.replace(tzinfo=UTC)
                    updated_at = ticket.updated_at
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=UTC)
                    performed_at = merge.performed_at
                    if performed_at.tzinfo is None:
                        performed_at = performed_at.replace(tzinfo=UTC)
                    if updated_at > original_dt and updated_at > performed_at:
                        conflicts.append(
                            {
                                "type": "ticket_modified",
                                "ticket_id": str(ticket_id),
                                "modified_at": ticket.updated_at.isoformat(),
                            }
                        )

        return conflicts

    async def _restore_ticket_states(
        self,
        merge: MergeOperation,
        partition_key: str,
    ) -> None:
        """Restore tickets to their pre-merge state."""
        now = datetime.now(UTC)

        for ticket_id in merge.secondary_ticket_ids:
            ticket = await self._ticket_repo.get_by_id(ticket_id, partition_key)
            if ticket:
                # Restore cluster assignment
                original_state = merge.get_snapshot(ticket_id) or {}
                original_cluster_id = original_state.get("clusterId")

                ticket.merged_into_id = None
                ticket.cluster_id = UUID(original_cluster_id) if original_cluster_id else None
                ticket.updated_at = now

                await self._ticket_repo.update(ticket, partition_key)

    async def get_merge_history(
        self,
        cluster_id: UUID,
        partition_key: str,
    ) -> list[MergeOperation]:
        """
        Get merge history for a cluster.

        Args:
            cluster_id: Cluster ID.
            partition_key: Partition key.

        Returns:
            List of merge operations for the cluster.
        """
        return await self._merge_repo.get_by_cluster_id(cluster_id, partition_key)

    async def check_revert_eligible(
        self,
        merge_id: UUID,
        partition_key: str,
    ) -> dict[str, Any]:
        """
        Check if a merge can be reverted.

        Args:
            merge_id: Merge operation ID.
            partition_key: Partition key.

        Returns:
            Dictionary with eligibility status and any issues.
        """
        merge = await self._merge_repo.get_by_id(merge_id, partition_key)
        if not merge:
            return {"eligible": False, "reason": "Merge not found"}

        if merge.status == MergeStatus.REVERTED:
            return {"eligible": False, "reason": "Already reverted"}

        now = datetime.now(UTC)
        revert_deadline = merge.revert_deadline
        if revert_deadline and revert_deadline.tzinfo is None:
            revert_deadline = revert_deadline.replace(tzinfo=UTC)
        if revert_deadline and now > revert_deadline:
            return {
                "eligible": False,
                "reason": "Revert window expired",
                "expired_at": revert_deadline.isoformat(),
            }

        conflicts = await self._check_revert_conflicts(merge, partition_key)
        if conflicts:
            return {
                "eligible": True,
                "has_conflicts": True,
                "conflicts": conflicts,
                "message": "Revert possible but has conflicts",
            }

        return {"eligible": True, "has_conflicts": False}
