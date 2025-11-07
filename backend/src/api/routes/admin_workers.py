"""
Admin Workers Routes - Worker listing and filtering for operations dashboard.

Provides:
- GET /admin/workers: List all workers with performance data
- Filters: low_rating, high_workload, at_risk, active
- Pagination support
- Performance signals: ratings, punctuality, workload

Used by: Operations managers to identify workers needing attention (US3, FR-009)
"""
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.lib.db import get_db
from src.lib.logging import get_logger
from src.models.workers import Worker
from src.models.users import User
from src.models.bookings import Booking
from src.models.reviews import Review


logger = get_logger(__name__)
router = APIRouter(prefix="/admin/workers", tags=["admin", "workers"])


# Response models
class WorkerPerformanceSignals(BaseModel):
    """Performance signals for a worker."""
    total_bookings: int = Field(description="Total bookings in period")
    average_rating: Optional[float] = Field(description="Average rating (1-5)")
    review_count: int = Field(description="Number of reviews")
    recent_coaching: int = Field(description="Coaching messages in last 30 days")
    punctuality_estimate: float = Field(description="Estimated punctuality % (placeholder)")


class WorkerListItem(BaseModel):
    """Worker list item with basic info and performance."""
    id: UUID
    name: str
    phone_number: Optional[str]
    email: Optional[str]
    skills: List[str]
    is_available: bool
    opt_in_voice: bool
    performance: WorkerPerformanceSignals
    flags: List[str] = Field(
        description="Performance flags: low_rating, high_workload, at_risk"
    )


class WorkerListResponse(BaseModel):
    """Paginated worker list response."""
    workers: List[WorkerListItem]
    total: int
    page: int
    page_size: int
    has_next: bool


@router.get(
    "",
    response_model=WorkerListResponse,
    summary="List workers with filters",
    description="Get paginated list of workers with performance data and filters",
)
def list_workers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    low_rating: Optional[bool] = Query(None, description="Filter: avg rating < 4.0"),
    high_workload: Optional[bool] = Query(None, description="Filter: bookings > threshold"),
    at_risk: Optional[bool] = Query(None, description="Filter: burnout risk"),
    active_only: bool = Query(True, description="Show only available workers"),
    days: int = Query(30, ge=1, le=365, description="Days to look back for metrics"),
    db: Session = Depends(get_db),
) -> WorkerListResponse:
    """
    List workers with performance data and optional filters.
    
    Filters:
    - low_rating: Workers with average rating < 4.0
    - high_workload: Workers with bookings > 1.5x average
    - at_risk: Workers at burnout risk (placeholder)
    - active_only: Show only available workers
    
    Performance signals include:
    - Total bookings
    - Average rating
    - Review count
    - Recent coaching messages
    - Punctuality estimate
    
    Args:
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
        low_rating: Filter for low-rated workers
        high_workload: Filter for high workload
        at_risk: Filter for at-risk workers
        active_only: Show only available workers
        days: Days to look back for metrics
        db: Database session
        
    Returns:
        WorkerListResponse with paginated workers
    """
    logger.info(
        f"GET /admin/workers (page={page}, filters: low_rating={low_rating}, "
        f"high_workload={high_workload}, at_risk={at_risk})"
    )
    
    # Date range for metrics
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Base query: Get all workers with user data
    base_query = (
        select(Worker, User)
        .join(User, Worker.id == User.id)
    )
    
    # Apply active filter
    if active_only:
        base_query = base_query.where(Worker.is_active == True)
    
    # Execute base query to get all workers (we'll filter in Python for simplicity)
    result = db.execute(base_query).all()
    workers_data = [(worker, user) for worker, user in result]
    
    # Calculate performance for each worker and apply filters
    filtered_workers = []
    
    for worker, user in workers_data:
        # Calculate performance signals
        performance = _calculate_worker_performance(
            db, worker.id, start_date, end_date
        )
        
        # Determine flags
        flags = []
        if performance['average_rating'] and performance['average_rating'] < 4.0:
            flags.append('low_rating')
        
        # High workload: bookings > threshold (placeholder: > 50 in period)
        if performance['total_bookings'] > 50:
            flags.append('high_workload')
        
        # At risk: placeholder logic
        if performance['average_rating'] and performance['average_rating'] < 3.5:
            flags.append('at_risk')
        
        # Apply filters
        if low_rating is not None and low_rating:
            if 'low_rating' not in flags:
                continue
        
        if high_workload is not None and high_workload:
            if 'high_workload' not in flags:
                continue
        
        if at_risk is not None and at_risk:
            if 'at_risk' not in flags:
                continue
        
        # Build worker item
        worker_item = {
            'id': worker.id,
            'name': user.name,
            'phone_number': user.phone,
            'email': user.email,
            'skills': worker.skills or [],
            'is_available': worker.is_active,
            'opt_in_voice': worker.opt_in_voice,
            'performance': performance,
            'flags': flags,
        }
        
        filtered_workers.append(worker_item)
    
    # Pagination
    total = len(filtered_workers)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_workers = filtered_workers[start_idx:end_idx]
    has_next = end_idx < total
    
    logger.info(
        f"Found {total} workers, returning page {page} ({len(paginated_workers)} items)"
    )
    
    return WorkerListResponse(
        workers=[WorkerListItem(**w) for w in paginated_workers],
        total=total,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


def _calculate_worker_performance(
    db: Session,
    worker_id: UUID,
    start_date: datetime,
    end_date: datetime,
) -> dict:
    """
    Calculate performance signals for a worker.
    
    Args:
        db: Database session
        worker_id: Worker UUID
        start_date: Start of period
        end_date: End of period
        
    Returns:
        WorkerPerformanceSignals as dict
    """
    # Total bookings
    stmt_bookings = (
        select(func.count(Booking.id))
        .where(
            and_(
                Booking.worker_id == worker_id,
                Booking.created_at.between(start_date, end_date),
            )
        )
    )
    total_bookings = db.execute(stmt_bookings).scalar() or 0
    
    # Average rating and review count
    stmt_rating = (
        select(
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count')
        )
        .select_from(Review)
        .join(Booking, Review.booking_id == Booking.id)
        .where(
            and_(
                Booking.worker_id == worker_id,
                Booking.created_at.between(start_date, end_date),
            )
        )
    )
    rating_result = db.execute(stmt_rating).one()
    average_rating = float(rating_result.avg_rating) if rating_result.avg_rating else None
    review_count = rating_result.review_count or 0
    
    if average_rating:
        average_rating = round(average_rating, 2)
    
    # Recent coaching (last 30 days)
    from src.models.ai_messages import AIMessage, DeliveryStatus
    coaching_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    stmt_coaching = (
        select(func.count(AIMessage.id))
        .where(
            and_(
                AIMessage.user_id == worker_id,
                AIMessage.agent_type == 'coachnova',
                AIMessage.delivery_status == DeliveryStatus.SENT,
                AIMessage.sent_at >= coaching_cutoff,
            )
        )
    )
    recent_coaching = db.execute(stmt_coaching).scalar() or 0
    
    # Punctuality estimate (placeholder)
    punctuality_estimate = 85.0
    
    return {
        'total_bookings': total_bookings,
        'average_rating': average_rating,
        'review_count': review_count,
        'recent_coaching': recent_coaching,
        'punctuality_estimate': punctuality_estimate,
    }


@router.get(
    "/{worker_id}",
    response_model=WorkerListItem,
    summary="Get worker details",
    description="Get detailed information for a specific worker",
)
def get_worker_details(
    worker_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Days to look back for metrics"),
    db: Session = Depends(get_db),
) -> WorkerListItem:
    """
    Get detailed information for a specific worker.
    
    Args:
        worker_id: Worker UUID
        days: Days to look back for metrics
        db: Database session
        
    Returns:
        WorkerListItem with performance data
    """
    logger.info(f"GET /admin/workers/{worker_id}")
    
    # Get worker and user
    stmt = (
        select(Worker, User)
        .join(User, Worker.id == User.id)
        .where(Worker.id == worker_id)
    )
    result = db.execute(stmt).one_or_none()
    
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found")
    
    worker, user = result
    
    # Calculate performance
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    performance = _calculate_worker_performance(db, worker_id, start_date, end_date)
    
    # Determine flags
    flags = []
    if performance.average_rating and performance.average_rating < 4.0:
        flags.append('low_rating')
    if performance.total_bookings > 50:
        flags.append('high_workload')
    if performance.average_rating and performance.average_rating < 3.5:
        flags.append('at_risk')
    
    return WorkerListItem(
        id=worker.id,
        name=user.name,
        phone_number=user.phone,
        email=user.email,
        skills=worker.skills or [],
        is_available=worker.is_active,
        opt_in_voice=worker.opt_in_voice,
        performance=performance,
        flags=flags,
    )
