"""
SpikeAlert domain model.

Represents a detected volume anomaly for spike detection (FR-014, FR-015, FR-016).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SpikeStatus(StrEnum):
    """Spike alert status."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class SeverityLevel(StrEnum):
    """Spike severity level based on percentage increase."""

    LOW = "low"  # 150-200% increase
    MEDIUM = "medium"  # 200-300% increase
    HIGH = "high"  # 300%+ increase


class SpikeAlert(BaseModel):
    """
    SpikeAlert entity for volume anomaly detection.

    Aligned with data-model.md spikes container schema.
    """

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Spike alert identifier")
    pk: str = Field(description="Partition key: {year-month}")

    # Alert state
    status: SpikeStatus = Field(default=SpikeStatus.ACTIVE)
    severity: SeverityLevel = Field(description="Alert severity based on increase %")

    # Field being monitored
    field_name: str = Field(description="Field name (category, channel, etc)")
    field_value: str = Field(description="Field value that spiked")

    # Volume metrics
    current_count: int = Field(ge=0, description="Current period volume")
    baseline_count: float = Field(ge=0, description="Historical baseline average")
    percentage_increase: float = Field(description="Percentage increase vs baseline")

    # Time window
    time_window_start: datetime = Field(description="Start of measurement window")
    time_window_end: datetime = Field(description="End of measurement window")

    # Related clusters for drill-down (FR-016)
    affected_cluster_ids: list[UUID] = Field(default_factory=list)

    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_by: str | None = Field(default=None)
    acknowledged_at: datetime | None = Field(default=None)
    resolved_at: datetime | None = Field(default=None)

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        doc["affectedClusterIds"] = [str(cid) for cid in self.affected_cluster_ids]
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> SpikeAlert:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    @staticmethod
    def generate_partition_key(timestamp: datetime) -> str:
        """Generate partition key from timestamp."""
        return timestamp.strftime("%Y-%m")

    @staticmethod
    def calculate_severity(percentage_increase: float) -> SeverityLevel:
        """Determine severity based on percentage increase."""
        if percentage_increase >= 300:
            return SeverityLevel.HIGH
        if percentage_increase >= 200:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW

    def acknowledge(self, actor_id: str) -> None:
        """Acknowledge the spike alert."""
        if self.status != SpikeStatus.ACTIVE:
            msg = f"Cannot acknowledge spike in {self.status} state"
            raise ValueError(msg)
        self.status = SpikeStatus.ACKNOWLEDGED
        self.acknowledged_by = actor_id
        self.acknowledged_at = datetime.utcnow()

    def resolve(self) -> None:
        """Resolve the spike alert."""
        if self.status == SpikeStatus.RESOLVED:
            msg = "Spike is already resolved"
            raise ValueError(msg)
        self.status = SpikeStatus.RESOLVED
        self.resolved_at = datetime.utcnow()

    def add_affected_cluster(self, cluster_id: UUID) -> None:
        """Add a cluster affected by this spike."""
        if cluster_id not in self.affected_cluster_ids:
            self.affected_cluster_ids.append(cluster_id)
