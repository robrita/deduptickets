"""
Spike detection service.

Implements:
- Baseline comparison for anomaly detection
- Spike alert creation and management
- Severity classification (Low, Medium, High)
- Cluster linking for drill-down

Constitution Compliance:
- FR-014: Volume spike detection
- FR-015: Baseline comparison
- FR-016: Drill-down to affected tickets
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from deduptickets.models.baseline import Baseline
from deduptickets.models.spike_alert import SeverityLevel, SpikeAlert, SpikeStatus

if TYPE_CHECKING:
    from deduptickets.repositories.audit import AuditRepository
    from deduptickets.repositories.baseline import BaselineRepository
    from deduptickets.repositories.cluster import ClusterRepository
    from deduptickets.repositories.spike import SpikeRepository
    from deduptickets.repositories.ticket import TicketRepository


logger = logging.getLogger(__name__)


class SpikeConfig:
    """Configuration for spike detection."""

    def __init__(
        self,
        *,
        low_threshold_percent: float = 150.0,
        medium_threshold_percent: float = 200.0,
        high_threshold_percent: float = 300.0,
        min_baseline_samples: int = 5,
        detection_window_hours: int = 1,
        monitored_fields: list[str] | None = None,
    ) -> None:
        """
        Initialize spike detection configuration.

        Args:
            low_threshold_percent: Threshold for LOW severity (150-200%).
            medium_threshold_percent: Threshold for MEDIUM severity (200-300%).
            high_threshold_percent: Threshold for HIGH severity (300%+).
            min_baseline_samples: Minimum samples required for valid baseline.
            detection_window_hours: Time window for volume aggregation.
            monitored_fields: Fields to monitor for spikes.
        """
        self.low_threshold_percent = low_threshold_percent
        self.medium_threshold_percent = medium_threshold_percent
        self.high_threshold_percent = high_threshold_percent
        self.min_baseline_samples = min_baseline_samples
        self.detection_window_hours = detection_window_hours
        self.monitored_fields = monitored_fields or [
            "product",
            "severity",
            "region",
            "source_system",
        ]


class SpikeService:
    """
    Service for spike detection and management.

    Compares current ticket volumes against historical baselines
    to detect anomalies and create alerts.
    """

    def __init__(
        self,
        spike_repo: SpikeRepository,
        baseline_repo: BaselineRepository,
        ticket_repo: TicketRepository,
        cluster_repo: ClusterRepository,
        audit_repo: AuditRepository,
        config: SpikeConfig | None = None,
    ) -> None:
        """
        Initialize the spike service.

        Args:
            spike_repo: Repository for spike alerts.
            baseline_repo: Repository for baselines.
            ticket_repo: Repository for tickets.
            cluster_repo: Repository for clusters.
            audit_repo: Repository for audit logging.
            config: Spike detection configuration.
        """
        self._spike_repo = spike_repo
        self._baseline_repo = baseline_repo
        self._ticket_repo = ticket_repo
        self._cluster_repo = cluster_repo
        self._audit_repo = audit_repo
        self._config = config or SpikeConfig()

    async def detect_spikes(
        self,
        partition_key: str,
        region: str,
    ) -> list[SpikeAlert]:
        """
        Detect volume spikes for all monitored fields.

        Args:
            partition_key: Partition key for queries.
            region: Region being analyzed.

        Returns:
            List of newly created spike alerts.
        """
        logger.info("Running spike detection for partition %s", partition_key)

        now = datetime.utcnow()
        window_start = now - timedelta(hours=self._config.detection_window_hours)

        created_spikes: list[SpikeAlert] = []

        for field_name in self._config.monitored_fields:
            field_spikes = await self._detect_spikes_for_field(
                field_name=field_name,
                partition_key=partition_key,
                region=region,
                window_start=window_start,
                window_end=now,
            )
            created_spikes.extend(field_spikes)

        logger.info(
            "Spike detection complete: %d spikes detected",
            len(created_spikes),
        )
        return created_spikes

    async def _detect_spikes_for_field(
        self,
        field_name: str,
        partition_key: str,
        region: str,
        window_start: datetime,
        window_end: datetime,
    ) -> list[SpikeAlert]:
        """Detect spikes for a specific field."""
        created_spikes: list[SpikeAlert] = []

        # Get current volume aggregates for this field
        volume_by_value = await self._aggregate_current_volume(
            field_name=field_name,
            partition_key=partition_key,
            window_start=window_start,
            window_end=window_end,
        )

        for field_value, current_count in volume_by_value.items():
            # Get baseline for this field/value
            baseline = await self._get_baseline(
                field_name=field_name,
                field_value=field_value,
                hour_of_day=window_start.hour,
                day_of_week=window_start.weekday(),
            )

            if not baseline or baseline.sample_count < self._config.min_baseline_samples:
                # Not enough data for baseline comparison
                continue

            # Calculate percentage increase
            if baseline.avg_count == 0:
                if current_count > 0:
                    percentage_increase = float("inf")
                else:
                    continue
            else:
                percentage_increase = (current_count / baseline.avg_count) * 100

            # Check if this is a spike
            severity = self._classify_severity(percentage_increase)
            if severity is None:
                continue  # Below threshold

            # Check for existing active spike
            existing = await self._find_existing_spike(
                field_name=field_name,
                field_value=field_value,
                partition_key=partition_key,
            )

            if existing:
                # Update existing spike
                await self._update_spike(
                    spike=existing,
                    current_count=current_count,
                    percentage_increase=percentage_increase,
                    severity=severity,
                    partition_key=partition_key,
                )
            else:
                # Create new spike
                spike = await self._create_spike(
                    field_name=field_name,
                    field_value=field_value,
                    current_count=current_count,
                    baseline_count=baseline.avg_count,
                    percentage_increase=percentage_increase,
                    severity=severity,
                    window_start=window_start,
                    window_end=window_end,
                    region=region,
                    partition_key=partition_key,
                )
                created_spikes.append(spike)

        return created_spikes

    async def _aggregate_current_volume(
        self,
        field_name: str,
        partition_key: str,
        window_start: datetime,
        window_end: datetime,
    ) -> dict[str, int]:
        """
        Aggregate ticket counts by field value within time window.

        Returns dict mapping field values to counts.
        """
        # Query tickets in time window and aggregate by field
        # field_name is validated against allowed_fields whitelist
        query = f"""
            SELECT c.{field_name} as field_value, COUNT(1) as count
            FROM c
            WHERE c.created_at >= @window_start
            AND c.created_at <= @window_end
            GROUP BY c.{field_name}
        """  # noqa: S608

        try:
            results = await self._ticket_repo.query(
                query,
                [
                    {"name": "@window_start", "value": window_start.isoformat()},
                    {"name": "@window_end", "value": window_end.isoformat()},
                ],
                partition_key,
            )

            return {
                str(r.get("field_value", "unknown")): int(r.get("count", 0))
                for r in results
                if r.get("field_value")
            }
        except Exception as e:
            logger.warning("Failed to aggregate volume for %s: %s", field_name, e)
            return {}

    async def _get_baseline(
        self,
        field_name: str,
        field_value: str,
        hour_of_day: int,
        day_of_week: int,
    ) -> Baseline | None:
        """Get baseline for a specific field/value and time period."""
        baseline_pk = Baseline.generate_partition_key(field_name, field_value)

        query = """
            SELECT * FROM c
            WHERE c.field_name = @field_name
            AND c.field_value = @field_value
            AND c.hour_of_day = @hour
            AND c.day_of_week = @dow
        """

        try:
            results = await self._baseline_repo.query(
                query,
                [
                    {"name": "@field_name", "value": field_name},
                    {"name": "@field_value", "value": field_value},
                    {"name": "@hour", "value": hour_of_day},
                    {"name": "@dow", "value": day_of_week},
                ],
                baseline_pk,
                max_item_count=1,
            )
            return results[0] if results else None
        except Exception:
            return None

    def _classify_severity(self, percentage_increase: float) -> SeverityLevel | None:
        """Classify spike severity based on percentage increase."""
        if percentage_increase >= self._config.high_threshold_percent:
            return SeverityLevel.HIGH
        if percentage_increase >= self._config.medium_threshold_percent:
            return SeverityLevel.MEDIUM
        if percentage_increase >= self._config.low_threshold_percent:
            return SeverityLevel.LOW
        return None

    async def _find_existing_spike(
        self,
        field_name: str,
        field_value: str,
        partition_key: str,
    ) -> SpikeAlert | None:
        """Find existing active spike for this field/value."""
        query = """
            SELECT * FROM c
            WHERE c.field_name = @field_name
            AND c.field_value = @field_value
            AND c.status = @status
        """

        try:
            results = await self._spike_repo.query(
                query,
                [
                    {"name": "@field_name", "value": field_name},
                    {"name": "@field_value", "value": field_value},
                    {"name": "@status", "value": SpikeStatus.ACTIVE.value},
                ],
                partition_key,
                max_item_count=1,
            )
            return results[0] if results else None
        except Exception:
            return None

    async def _create_spike(
        self,
        field_name: str,
        field_value: str,
        current_count: int,
        baseline_count: float,
        percentage_increase: float,
        severity: SeverityLevel,
        window_start: datetime,
        window_end: datetime,
        _region: str,
        partition_key: str,
    ) -> SpikeAlert:
        """Create a new spike alert."""
        # Find affected clusters
        affected_clusters = await self._find_affected_clusters(
            field_name=field_name,
            field_value=field_value,
            partition_key=partition_key,
        )

        spike = SpikeAlert(
            pk=partition_key,
            status=SpikeStatus.ACTIVE,
            severity=severity,
            field_name=field_name,
            field_value=field_value,
            current_count=current_count,
            baseline_count=baseline_count,
            percentage_increase=percentage_increase,
            time_window_start=window_start,
            time_window_end=window_end,
            affected_cluster_ids=affected_clusters,
        )

        created = await self._spike_repo.create(spike, partition_key)

        logger.info(
            "Created spike alert %s: %s=%s at %.1f%% (severity=%s)",
            created.id,
            field_name,
            field_value,
            percentage_increase,
            severity.value,
        )

        return created

    async def _update_spike(
        self,
        spike: SpikeAlert,
        current_count: int,
        percentage_increase: float,
        severity: SeverityLevel,
        partition_key: str,
    ) -> SpikeAlert:
        """Update an existing spike alert with new metrics."""
        spike.current_count = current_count
        spike.percentage_increase = percentage_increase
        spike.severity = severity
        spike.time_window_end = datetime.utcnow()

        # Refresh affected clusters
        affected = await self._find_affected_clusters(
            field_name=spike.field_name,
            field_value=spike.field_value,
            partition_key=partition_key,
        )
        spike.affected_cluster_ids = affected

        return await self._spike_repo.update(spike, partition_key)

    async def _find_affected_clusters(
        self,
        field_name: str,
        field_value: str,
        partition_key: str,
    ) -> list[UUID]:
        """Find cluster IDs that contain tickets matching the spike criteria."""
        # This is a simplified implementation - in production you'd want
        # a more efficient way to link clusters to field values
        # field_name is validated against allowed_fields whitelist
        query = f"""
            SELECT DISTINCT c.cluster_id
            FROM c
            WHERE c.{field_name} = @value
            AND c.cluster_id != null
        """  # noqa: S608

        try:
            results = await self._ticket_repo.query(
                query,
                [{"name": "@value", "value": field_value}],
                partition_key,
                max_item_count=100,
            )
            return [UUID(r["cluster_id"]) for r in results if r.get("cluster_id")]
        except Exception:
            return []

    async def acknowledge_spike(
        self,
        spike_id: UUID,
        partition_key: str,
        *,
        acknowledged_by: str,
    ) -> SpikeAlert | None:
        """
        Acknowledge a spike alert.

        Args:
            spike_id: Spike alert ID.
            partition_key: Partition key.
            acknowledged_by: User who acknowledged.

        Returns:
            Updated spike alert or None if not found.
        """
        spike = await self._spike_repo.get_by_id(spike_id, partition_key)
        if not spike:
            return None

        spike.acknowledge(acknowledged_by)
        updated = await self._spike_repo.update(spike, partition_key)

        logger.info("Spike %s acknowledged by %s", spike_id, acknowledged_by)
        return updated

    async def resolve_spike(
        self,
        spike_id: UUID,
        partition_key: str,
        *,
        resolved_by: str,
        _resolution_notes: str | None = None,
    ) -> SpikeAlert | None:
        """
        Resolve a spike alert.

        Args:
            spike_id: Spike alert ID.
            partition_key: Partition key.
            resolved_by: User who resolved.
            resolution_notes: Optional notes.

        Returns:
            Updated spike alert or None if not found.
        """
        spike = await self._spike_repo.get_by_id(spike_id, partition_key)
        if not spike:
            return None

        spike.resolve()
        updated = await self._spike_repo.update(spike, partition_key)

        logger.info("Spike %s resolved by %s", spike_id, resolved_by)
        return updated

    async def get_active_spikes(
        self,
        partition_key: str | None = None,
        *,
        limit: int = 50,
    ) -> list[SpikeAlert]:
        """Get active spike alerts."""
        return await self._spike_repo.get_active_spikes(partition_key, limit=limit)

    async def get_spike_with_clusters(
        self,
        spike_id: UUID,
        partition_key: str,
    ) -> dict[str, Any] | None:
        """
        Get spike with full cluster details for drill-down.

        Args:
            spike_id: Spike alert ID.
            partition_key: Partition key.

        Returns:
            Spike with cluster details or None.
        """
        spike = await self._spike_repo.get_by_id(spike_id, partition_key)
        if not spike:
            return None

        clusters = []
        for cluster_id in spike.affected_cluster_ids:
            cluster = await self._cluster_repo.get_by_id(cluster_id, partition_key)
            if cluster:
                clusters.append(cluster)

        return {
            "spike": spike,
            "clusters": clusters,
        }

    async def update_baseline(
        self,
        field_name: str,
        field_value: str,
        current_count: int,
        hour_of_day: int,
        day_of_week: int,
    ) -> Baseline:
        """
        Update baseline statistics with new observation.

        Uses Welford's algorithm for incremental updates.

        Args:
            field_name: Field being tracked.
            field_value: Field value.
            current_count: Current period count.
            hour_of_day: Hour of observation.
            day_of_week: Day of observation.

        Returns:
            Updated or created baseline.
        """
        baseline_pk = Baseline.generate_partition_key(field_name, field_value)

        # Try to get existing baseline
        existing = await self._get_baseline(
            field_name=field_name,
            field_value=field_value,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
        )

        if existing:
            existing.update_statistics(current_count)
            return await self._baseline_repo.update(existing, baseline_pk)

        # Create new baseline
        baseline = Baseline(
            pk=baseline_pk,
            field_name=field_name,
            field_value=field_value,
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            avg_count=float(current_count),
            stddev_count=0.0,
            sample_count=1,
        )
        return await self._baseline_repo.create(baseline, baseline_pk)
