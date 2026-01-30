"""
Spike detection background worker.

Runs periodically to:
1. Aggregate ticket volumes by monitored fields
2. Compare against historical baselines
3. Create/update spike alerts
4. Update baselines with new observations

Constitution Compliance:
- FR-014: Volume spike detection
- Principle VIII: Async-first operations
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deduptickets.services.spike_service import SpikeService


logger = logging.getLogger(__name__)


class SpikeDetectionWorker:
    """
    Background worker for spike detection.

    Runs every N minutes to check for volume anomalies.
    """

    def __init__(
        self,
        spike_service: SpikeService,
        *,
        interval_minutes: int = 15,
        regions: list[str] | None = None,
    ) -> None:
        """
        Initialize the spike detection worker.

        Args:
            spike_service: Service for spike detection.
            interval_minutes: How often to run detection (default 15 min).
            regions: List of regions to monitor.
        """
        self._spike_service = spike_service
        self._interval_minutes = interval_minutes
        self._regions = regions or ["US", "EU", "APAC"]
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            logger.warning("Spike detection worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "Spike detection worker started (interval=%d min, regions=%s)",
            self._interval_minutes,
            self._regions,
        )

    async def stop(self) -> None:
        """Stop the background worker gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Spike detection worker stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                await self._run_detection_cycle()
            except Exception as e:
                logger.exception("Spike detection cycle failed: %s", e)

            # Wait for next interval
            await asyncio.sleep(self._interval_minutes * 60)

    async def _run_detection_cycle(self) -> None:
        """Run a single detection cycle for all regions."""
        logger.info("Starting spike detection cycle")
        start_time = datetime.utcnow()
        total_spikes = 0

        for region in self._regions:
            try:
                partition_key = self._build_partition_key(region)
                spikes = await self._spike_service.detect_spikes(
                    partition_key=partition_key,
                    region=region,
                )
                total_spikes += len(spikes)

                # Also update baselines
                await self._update_baselines_for_region(region, partition_key)

            except Exception as e:
                logger.error("Detection failed for region %s: %s", region, e)

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            "Spike detection cycle complete: %d spikes in %.2fs",
            total_spikes,
            elapsed,
        )

    async def _update_baselines_for_region(
        self,
        _region: str,
        partition_key: str,
    ) -> None:
        """Update baselines with current observations for a region."""
        now = datetime.utcnow()
        hour_of_day = now.hour
        day_of_week = now.weekday()

        # Get current volume aggregates for each monitored field
        for field_name in self._spike_service._config.monitored_fields:
            window_start = now - timedelta(hours=1)

            volume_by_value = await self._spike_service._aggregate_current_volume(
                field_name=field_name,
                partition_key=partition_key,
                window_start=window_start,
                window_end=now,
            )

            # Update baselines for each field value
            for field_value, current_count in volume_by_value.items():
                try:
                    await self._spike_service.update_baseline(
                        field_name=field_name,
                        field_value=field_value,
                        current_count=current_count,
                        hour_of_day=hour_of_day,
                        day_of_week=day_of_week,
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to update baseline for %s=%s: %s",
                        field_name,
                        field_value,
                        e,
                    )

    @staticmethod
    def _build_partition_key(region: str) -> str:
        """Build partition key from region."""
        now = datetime.utcnow()
        return f"{region}|{now.strftime('%Y-%m')}"

    async def run_once(self, region: str | None = None) -> list:
        """
        Run detection cycle once (for testing/manual trigger).

        Args:
            region: Optional single region to check.

        Returns:
            List of detected spikes.
        """
        regions = [region] if region else self._regions
        all_spikes = []

        for r in regions:
            partition_key = self._build_partition_key(r)
            spikes = await self._spike_service.detect_spikes(
                partition_key=partition_key,
                region=r,
            )
            all_spikes.extend(spikes)

        return all_spikes


async def create_spike_worker(
    spike_service: SpikeService,
    *,
    interval_minutes: int = 15,
    regions: list[str] | None = None,
) -> SpikeDetectionWorker:
    """
    Factory function to create and configure spike worker.

    Args:
        spike_service: Spike detection service.
        interval_minutes: Detection interval.
        regions: Regions to monitor.

    Returns:
        Configured worker instance.
    """
    return SpikeDetectionWorker(
        spike_service,
        interval_minutes=interval_minutes,
        regions=regions,
    )
