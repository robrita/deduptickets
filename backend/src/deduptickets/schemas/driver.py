"""
DTOs for driver/trend endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from deduptickets.schemas.common import PaginationMeta


class DriverResponse(BaseModel):
    """Response schema for a single driver."""

    id: UUID
    field_name: str
    field_value: str
    region: str
    cluster_count: int
    ticket_count: int
    avg_tickets_per_cluster: float
    week_over_week_growth: float
    period_start: datetime
    period_end: datetime


class TopDriversResponse(BaseModel):
    """Response for top drivers ranked by cluster count."""

    drivers: list[DriverResponse]
    period_start: datetime
    period_end: datetime
    total_clusters: int = Field(
        description="Total clusters across all drivers",
    )


class FastestGrowingResponse(BaseModel):
    """Response for fastest growing drivers by week-over-week growth."""

    drivers: list[DriverResponse]
    period_start: datetime
    period_end: datetime
    min_cluster_threshold: int = Field(
        description="Minimum clusters to be included in ranking",
    )


class MostDuplicatedResponse(BaseModel):
    """Response for drivers with highest tickets-per-cluster ratio."""

    drivers: list[DriverResponse]
    period_start: datetime
    period_end: datetime
    avg_duplication_ratio: float = Field(
        description="Average tickets per cluster across all drivers",
    )


class TrendDataPoint(BaseModel):
    """A single data point in a trend series."""

    date: str
    value: float
    label: str | None = None


class TrendSeriesResponse(BaseModel):
    """Response for a time series of trend data."""

    series_name: str
    data_points: list[TrendDataPoint]
    from_date: datetime
    to_date: datetime


class DriverListResponse(BaseModel):
    """Paginated list of drivers."""

    items: list[DriverResponse]
    pagination: PaginationMeta
