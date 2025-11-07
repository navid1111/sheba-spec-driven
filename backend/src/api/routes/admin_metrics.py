"""
Admin Metrics Routes - Operations dashboard endpoints.

Provides read-only access to business metrics and analytics:
- GET /admin/metrics/overview: High-level summary
- GET /admin/metrics/engagement: Customer engagement by segment
- GET /admin/metrics/conversions: AI outreach effectiveness
- GET /admin/metrics/workers: Worker performance summary
- GET /admin/metrics/satisfaction-trend: Satisfaction over time

Used by: Operations managers for data-driven decisions (US3, FR-009)
"""
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.lib.db import get_db
from src.lib.logging import get_logger
from src.services.metrics_service import get_metrics_service, MetricsService
from pydantic import BaseModel, Field


logger = get_logger(__name__)
router = APIRouter(prefix="/admin/metrics", tags=["admin", "metrics"])


# Response models
class EngagementMetrics(BaseModel):
    """Customer engagement by segment."""
    total_customers: int
    new: dict  # {'count': int, 'engagement_rate': float}
    repeat: dict
    inactive: dict


class ConversionMetrics(BaseModel):
    """AI outreach conversion metrics."""
    messages_sent: int
    clicks: int
    click_rate: float = Field(description="Click-through rate (%)")
    bookings: int
    conversion_rate: float = Field(description="Booking conversion rate (%)")


class WorkerMetrics(BaseModel):
    """Worker performance summary."""
    total_workers: int
    average_rating: float
    punctuality_rate: float
    coaching_sent: int
    high_performers: int
    low_performers: int
    at_risk_count: int


class AlertsCount(BaseModel):
    """Active alerts count."""
    burnout: int
    low_rating: int
    high_absence: int
    total: int


class MetricsOverviewResponse(BaseModel):
    """Complete metrics overview."""
    engagement: EngagementMetrics
    conversions: ConversionMetrics
    workers: WorkerMetrics
    alerts: AlertsCount
    period: dict  # {'start': ISO string, 'end': ISO string}


class RatingDistributionResponse(BaseModel):
    """Rating distribution (1-5 stars)."""
    distribution: dict  # {1: count, 2: count, ...}
    total_reviews: int


class SatisfactionTrendPoint(BaseModel):
    """Single data point in satisfaction trend."""
    date: str  # ISO date
    avg_rating: float
    review_count: int


class SatisfactionTrendResponse(BaseModel):
    """Satisfaction trend over time."""
    trend: list[SatisfactionTrendPoint]
    period_days: int


@router.get(
    "/overview",
    response_model=MetricsOverviewResponse,
    summary="Get metrics overview",
    description="High-level summary of engagement, conversions, worker performance, and alerts",
)
def get_metrics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> MetricsOverviewResponse:
    """
    Get comprehensive metrics overview for dashboard.
    
    Includes:
    - Customer engagement by segment (new, repeat, inactive)
    - AI outreach conversion rates (messages → clicks → bookings)
    - Worker performance summary (ratings, coaching, high/low performers)
    - Active alerts count (burnout, low rating, high absence)
    
    Args:
        days: Number of days to look back (default: 30)
        db: Database session
        
    Returns:
        MetricsOverviewResponse with all metrics
    """
    logger.info(f"GET /admin/metrics/overview (days={days})")
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Get metrics
    metrics_service = get_metrics_service(db)
    overview = metrics_service.get_overview_metrics(start_date, end_date)
    
    logger.info(
        "Metrics overview calculated",
        extra={
            "days": days,
            "total_customers": overview['engagement']['total_customers'],
            "messages_sent": overview['conversions']['messages_sent'],
            "total_workers": overview['workers']['total_workers'],
        }
    )
    
    return MetricsOverviewResponse(**overview)


@router.get(
    "/engagement",
    response_model=EngagementMetrics,
    summary="Get engagement metrics",
    description="Customer engagement rates by segment (new, repeat, inactive)",
)
def get_engagement_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> EngagementMetrics:
    """
    Get customer engagement metrics by segment.
    
    Segments:
    - New: First booking in last 30 days
    - Repeat: 2+ bookings, active in last 30 days
    - Inactive: Last booking > 30 days ago
    
    Args:
        days: Number of days to look back (default: 30)
        db: Database session
        
    Returns:
        EngagementMetrics with segment breakdown
    """
    logger.info(f"GET /admin/metrics/engagement (days={days})")
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    metrics_service = get_metrics_service(db)
    engagement = metrics_service.get_engagement_by_segment(start_date, end_date)
    
    return EngagementMetrics(**engagement)


@router.get(
    "/conversions",
    response_model=ConversionMetrics,
    summary="Get conversion metrics",
    description="AI outreach effectiveness: messages → clicks → bookings",
)
def get_conversion_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> ConversionMetrics:
    """
    Get AI outreach conversion metrics.
    
    Tracks:
    - Messages sent (SmartEngage reminders)
    - Click-through rate (deeplink followed)
    - Booking conversion rate (bookings from outreach)
    
    Args:
        days: Number of days to look back (default: 30)
        db: Database session
        
    Returns:
        ConversionMetrics with rates
    """
    logger.info(f"GET /admin/metrics/conversions (days={days})")
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    metrics_service = get_metrics_service(db)
    conversions = metrics_service.get_conversion_metrics(start_date, end_date)
    
    return ConversionMetrics(**conversions)


@router.get(
    "/workers",
    response_model=WorkerMetrics,
    summary="Get worker performance summary",
    description="Aggregate worker performance: ratings, coaching, high/low performers",
)
def get_worker_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> WorkerMetrics:
    """
    Get worker performance summary.
    
    Includes:
    - Total active workers
    - Average rating
    - Punctuality rate
    - Coaching messages sent
    - High performers (rating >= 4.5)
    - Low performers (rating < 3.5)
    - At-risk count (burnout risk)
    
    Args:
        days: Number of days to look back (default: 30)
        db: Database session
        
    Returns:
        WorkerMetrics with performance summary
    """
    logger.info(f"GET /admin/metrics/workers (days={days})")
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    metrics_service = get_metrics_service(db)
    workers = metrics_service.get_worker_performance_summary(start_date, end_date)
    
    return WorkerMetrics(**workers)


@router.get(
    "/rating-distribution",
    response_model=RatingDistributionResponse,
    summary="Get rating distribution",
    description="Distribution of ratings (1-5 stars)",
)
def get_rating_distribution(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
) -> RatingDistributionResponse:
    """
    Get distribution of ratings across all workers.
    
    Args:
        days: Number of days to look back (default: 30)
        db: Database session
        
    Returns:
        RatingDistributionResponse with counts per rating
    """
    logger.info(f"GET /admin/metrics/rating-distribution (days={days})")
    
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    metrics_service = get_metrics_service(db)
    distribution = metrics_service.get_rating_distribution(start_date, end_date)
    total_reviews = sum(distribution.values())
    
    return RatingDistributionResponse(
        distribution=distribution,
        total_reviews=total_reviews,
    )


@router.get(
    "/satisfaction-trend",
    response_model=SatisfactionTrendResponse,
    summary="Get satisfaction trend",
    description="Satisfaction (rating) trend over time with configurable intervals",
)
def get_satisfaction_trend(
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
    interval_days: int = Query(7, ge=1, le=30, description="Days per data point"),
    db: Session = Depends(get_db),
) -> SatisfactionTrendResponse:
    """
    Get satisfaction trend over time.
    
    Returns time-series data of average ratings and review counts.
    
    Args:
        days: Number of days to look back (default: 30)
        interval_days: Days per data point (default: 7)
        db: Database session
        
    Returns:
        SatisfactionTrendResponse with trend data
    """
    logger.info(
        f"GET /admin/metrics/satisfaction-trend (days={days}, interval={interval_days})"
    )
    
    metrics_service = get_metrics_service(db)
    trend = metrics_service.get_satisfaction_trend(days, interval_days)
    
    return SatisfactionTrendResponse(
        trend=[SatisfactionTrendPoint(**point) for point in trend],
        period_days=days,
    )
