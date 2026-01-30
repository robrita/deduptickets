"""
Driver model for trend analysis.

A Driver represents a recurring theme or pattern in ticket clusters,
used for identifying top issues and trend analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Driver(BaseModel):
    """
    Represents a recurring pattern or theme identified from ticket clusters.

    Drivers aggregate cluster data by common fields (product, category, etc.)
    to help identify top issues and trending problems.
    """

    id: UUID = Field(default_factory=uuid4)

    # Identification
    field_name: str = Field(
        ...,
        description="The field used for grouping (e.g., 'product', 'category')",
    )
    field_value: str = Field(
        ...,
        description="The value of the grouping field",
    )
    region: str = Field(
        ...,
        description="Region for partitioning",
    )

    # Current metrics
    cluster_count: int = Field(
        default=0,
        ge=0,
        description="Number of clusters with this driver",
    )
    ticket_count: int = Field(
        default=0,
        ge=0,
        description="Total tickets across all clusters",
    )
    avg_tickets_per_cluster: float = Field(
        default=0.0,
        ge=0.0,
        description="Average tickets per cluster (duplication ratio)",
    )

    # Trend metrics
    previous_week_cluster_count: int = Field(
        default=0,
        ge=0,
        description="Cluster count from previous week for growth calc",
    )
    week_over_week_growth: float = Field(
        default=0.0,
        description="Week-over-week growth percentage",
    )

    # Timeframe
    period_start: datetime = Field(
        ...,
        description="Start of the analysis period",
    )
    period_end: datetime = Field(
        ...,
        description="End of the analysis period",
    )

    # Metadata
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(),
    )

    def compute_partition_key(self) -> str:
        """Compute partition key for Cosmos DB storage."""
        month = self.period_end.strftime("%Y-%m")
        return f"{self.region}|{month}"

    def calculate_growth(self) -> None:
        """Calculate week-over-week growth percentage."""
        if self.previous_week_cluster_count > 0:
            growth = (
                (self.cluster_count - self.previous_week_cluster_count)
                / self.previous_week_cluster_count
            ) * 100
            self.week_over_week_growth = round(growth, 2)
        else:
            # If no previous data, treat current count as 100% growth if > 0
            self.week_over_week_growth = 100.0 if self.cluster_count > 0 else 0.0

    def calculate_avg_tickets(self) -> None:
        """Calculate average tickets per cluster."""
        if self.cluster_count > 0:
            self.avg_tickets_per_cluster = round(self.ticket_count / self.cluster_count, 2)
        else:
            self.avg_tickets_per_cluster = 0.0

    class Config:
        """Pydantic configuration."""

        json_schema_extra: ClassVar[dict] = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "field_name": "product",
                "field_value": "Mobile Banking",
                "region": "US",
                "cluster_count": 45,
                "ticket_count": 180,
                "avg_tickets_per_cluster": 4.0,
                "previous_week_cluster_count": 30,
                "week_over_week_growth": 50.0,
                "period_start": "2025-01-20T00:00:00Z",
                "period_end": "2025-01-27T00:00:00Z",
                "last_updated": "2025-01-27T12:00:00Z",
            }
        }
