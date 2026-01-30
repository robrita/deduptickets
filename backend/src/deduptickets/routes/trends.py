"""
Trend analysis endpoints.

Provides ticket volume trends, top drivers, and baseline comparisons.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from deduptickets.schemas.driver import (
    DriverResponse,
    FastestGrowingResponse,
    MostDuplicatedResponse,
    TopDriversResponse,
)
from deduptickets.services.trend_service import TrendConfig, TrendService

if TYPE_CHECKING:
    from deduptickets.dependencies import (
        ApiKeyDep,
        AuditRepoDep,
        BaselineRepoDep,
        ClusterRepoDep,
        TicketRepoDep,
    )

router = APIRouter()


def get_trend_service(
    cluster_repo: ClusterRepoDep,
    ticket_repo: TicketRepoDep,
    audit_repo: AuditRepoDep,
) -> TrendService:
    """Dependency to create TrendService."""
    return TrendService(
        cluster_repo=cluster_repo,
        ticket_repo=ticket_repo,
        audit_repo=audit_repo,
        config=TrendConfig(),
    )


TrendServiceDep = Annotated[TrendService, Depends(get_trend_service)]


@router.get(
    "/top-drivers",
    response_model=TopDriversResponse,
    summary="Get top drivers",
    description="Get top drivers ranked by cluster count.",
)
async def get_top_drivers(
    trend_service: TrendServiceDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region to analyze")] = "US",
    field_name: Annotated[str, Query(description="Field to group by")] = "product",
    days: Annotated[int, Query(ge=1, le=90, description="Lookback days")] = 7,
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 10,
) -> TopDriversResponse:
    """Get top drivers ranked by cluster count."""
    drivers = await trend_service.get_top_drivers(region, field_name, days, limit)

    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)
    total_clusters = sum(d.cluster_count for d in drivers)

    return TopDriversResponse(
        drivers=[
            DriverResponse(
                id=d.id,
                field_name=d.field_name,
                field_value=d.field_value,
                region=d.region,
                cluster_count=d.cluster_count,
                ticket_count=d.ticket_count,
                avg_tickets_per_cluster=d.avg_tickets_per_cluster,
                week_over_week_growth=d.week_over_week_growth,
                period_start=d.period_start,
                period_end=d.period_end,
            )
            for d in drivers
        ],
        period_start=period_start,
        period_end=now,
        total_clusters=total_clusters,
    )


@router.get(
    "/fastest-growing",
    response_model=FastestGrowingResponse,
    summary="Get fastest growing drivers",
    description="Get drivers with highest week-over-week growth.",
)
async def get_fastest_growing(
    trend_service: TrendServiceDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region to analyze")] = "US",
    field_name: Annotated[str, Query(description="Field to group by")] = "product",
    days: Annotated[int, Query(ge=1, le=90, description="Lookback days")] = 7,
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 10,
    min_clusters: Annotated[int, Query(ge=1, description="Minimum clusters")] = 3,
) -> FastestGrowingResponse:
    """Get fastest growing drivers by week-over-week growth."""
    drivers = await trend_service.get_fastest_growing(region, field_name, days, limit, min_clusters)

    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    return FastestGrowingResponse(
        drivers=[
            DriverResponse(
                id=d.id,
                field_name=d.field_name,
                field_value=d.field_value,
                region=d.region,
                cluster_count=d.cluster_count,
                ticket_count=d.ticket_count,
                avg_tickets_per_cluster=d.avg_tickets_per_cluster,
                week_over_week_growth=d.week_over_week_growth,
                period_start=d.period_start,
                period_end=d.period_end,
            )
            for d in drivers
        ],
        period_start=period_start,
        period_end=now,
        min_cluster_threshold=min_clusters,
    )


@router.get(
    "/most-duplicated",
    response_model=MostDuplicatedResponse,
    summary="Get most duplicated drivers",
    description="Get drivers with highest tickets-per-cluster ratio.",
)
async def get_most_duplicated(
    trend_service: TrendServiceDep,
    _api_key: ApiKeyDep,
    region: Annotated[str, Query(description="Region to analyze")] = "US",
    field_name: Annotated[str, Query(description="Field to group by")] = "product",
    days: Annotated[int, Query(ge=1, le=90, description="Lookback days")] = 7,
    limit: Annotated[int, Query(ge=1, le=50, description="Max results")] = 10,
    min_clusters: Annotated[int, Query(ge=1, description="Minimum clusters")] = 2,
) -> MostDuplicatedResponse:
    """Get drivers with highest duplication ratio."""
    drivers = await trend_service.get_most_duplicated(region, field_name, days, limit, min_clusters)

    now = datetime.now(UTC)
    period_start = now - timedelta(days=days)

    # Calculate average duplication ratio
    total_tickets = sum(d.ticket_count for d in drivers)
    total_clusters = sum(d.cluster_count for d in drivers)
    avg_ratio = total_tickets / total_clusters if total_clusters > 0 else 0.0

    return MostDuplicatedResponse(
        drivers=[
            DriverResponse(
                id=d.id,
                field_name=d.field_name,
                field_value=d.field_value,
                region=d.region,
                cluster_count=d.cluster_count,
                ticket_count=d.ticket_count,
                avg_tickets_per_cluster=d.avg_tickets_per_cluster,
                week_over_week_growth=d.week_over_week_growth,
                period_start=d.period_start,
                period_end=d.period_end,
            )
            for d in drivers
        ],
        period_start=period_start,
        period_end=now,
        avg_duplication_ratio=round(avg_ratio, 2),
    )


@router.get(
    "/volume",
    summary="Get ticket volume trends",
    description="Get ticket volume over time for trend analysis.",
)
async def get_volume_trends(
    baseline_repo: BaselineRepoDep,
    _api_key: ApiKeyDep,
    product: Annotated[str, Query(description="Product to analyze")],
    days: Annotated[int, Query(ge=1, le=90, description="Number of days")] = 30,
) -> dict:
    """Get ticket volume trends for a product."""
    to_date = datetime.now(UTC)
    from_date = to_date - timedelta(days=days)

    # Get baselines for the date range
    baselines = await baseline_repo.get_date_range(product, from_date, to_date, partition_key=None)

    data_points = [
        {
            "date": b.date.strftime("%Y-%m-%d") if hasattr(b.date, "strftime") else str(b.date),
            "mean": b.mean_daily_count,
            "std": b.std_deviation,
        }
        for b in baselines
    ]

    return {
        "product": product,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "data_points": data_points,
    }


@router.get(
    "/products",
    summary="List products with baselines",
    description="Get list of products that have baseline data.",
)
async def list_products(
    baseline_repo: BaselineRepoDep,
    _api_key: ApiKeyDep,
) -> dict:
    """List all products with baseline data."""
    products = await baseline_repo.get_all_products()
    return {"products": products}


@router.get(
    "/baseline/{product}",
    summary="Get current baseline",
    description="Get the current baseline statistics for a product.",
    responses={
        404: {"description": "No baseline found"},
    },
)
async def get_baseline(
    product: str,
    baseline_repo: BaselineRepoDep,
    _api_key: ApiKeyDep,
) -> dict:
    """Get current baseline for a product."""
    baseline = await baseline_repo.get_latest_by_product(product)

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline found for product '{product}'",
        )

    date_str = (
        baseline.date.strftime("%Y-%m-%d")
        if hasattr(baseline.date, "strftime")
        else str(baseline.date)
    )
    return {
        "product": baseline.product,
        "region": baseline.region,
        "date": date_str,
        "mean_daily_count": baseline.mean_daily_count,
        "std_deviation": baseline.std_deviation,
        "rolling_window_days": baseline.rolling_window_days,
        "spike_threshold_2std": baseline.mean_daily_count + (2 * baseline.std_deviation),
        "spike_threshold_3std": baseline.mean_daily_count + (3 * baseline.std_deviation),
    }


@router.get(
    "/summary",
    summary="Get system-wide summary",
    description="Get a summary of ticket trends across all products.",
)
async def get_summary(
    baseline_repo: BaselineRepoDep,
    _api_key: ApiKeyDep,
) -> dict:
    """Get system-wide trend summary."""
    products = await baseline_repo.get_all_products()

    summaries = []
    for product in products:
        baseline = await baseline_repo.get_latest_by_product(product)
        if baseline:
            last_updated = (
                baseline.date.strftime("%Y-%m-%d")
                if hasattr(baseline.date, "strftime")
                else str(baseline.date)
            )
            summaries.append(
                {
                    "product": product,
                    "mean_daily_count": baseline.mean_daily_count,
                    "std_deviation": baseline.std_deviation,
                    "last_updated": last_updated,
                }
            )

    return {
        "product_count": len(products),
        "products": summaries,
        "generated_at": datetime.now(UTC).isoformat(),
    }
