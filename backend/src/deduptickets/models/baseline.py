"""
Baseline domain model.

Stores historical volume baselines for spike detection comparison.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Baseline(BaseModel):
    """
    Baseline entity for historical volume tracking.

    Aligned with data-model.md baselines container schema.
    Used by spike detection to compare current volume against historical patterns.
    """

    # Document identifiers
    id: UUID = Field(default_factory=uuid4, description="Baseline identifier")
    pk: str = Field(description="Partition key: {fieldName}|{fieldValue}")

    # Field being tracked
    field_name: str = Field(description="Field name (category, channel, etc)")
    field_value: str = Field(description="Field value")

    # Time dimensions for granular baselines
    hour_of_day: int = Field(ge=0, le=23, description="Hour of day (0-23)")
    day_of_week: int = Field(ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")

    # Statistical measures
    avg_count: float = Field(ge=0, description="Average ticket count for this period")
    stddev_count: float = Field(ge=0, description="Standard deviation")
    sample_count: int = Field(ge=0, description="Number of samples in calculation")

    # Metadata
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    def to_cosmos_document(self) -> dict[str, Any]:
        """Convert to Cosmos DB document format."""
        doc = self.model_dump(mode="json")
        doc["id"] = str(self.id)
        return doc

    @classmethod
    def from_cosmos_document(cls, doc: dict[str, Any]) -> Baseline:
        """Create from Cosmos DB document."""
        return cls.model_validate(doc)

    @staticmethod
    def generate_partition_key(field_name: str, field_value: str) -> str:
        """Generate partition key from field name and value."""
        return f"{field_name}|{field_value}"

    def update_statistics(self, new_count: int) -> None:
        """
        Update running statistics with a new sample using Welford's algorithm.

        This allows incremental updates without storing all historical data.
        """
        self.sample_count += 1
        delta = new_count - self.avg_count
        self.avg_count += delta / self.sample_count

        if self.sample_count > 1:
            delta2 = new_count - self.avg_count
            # Update variance using Welford's online algorithm
            m2 = (self.stddev_count**2) * (self.sample_count - 2) + delta * delta2
            self.stddev_count = (m2 / (self.sample_count - 1)) ** 0.5
        else:
            self.stddev_count = 0.0

        self.computed_at = datetime.utcnow()

    def is_spike(self, current_count: int, threshold_percent: float = 200.0) -> bool:
        """
        Check if current count represents a spike.

        Args:
            current_count: Current period ticket count.
            threshold_percent: Percentage increase to trigger spike (default 200%).

        Returns:
            True if current count exceeds threshold.
        """
        if self.avg_count == 0:
            return current_count > 0
        percentage_increase = (current_count / self.avg_count) * 100
        return percentage_increase >= threshold_percent
