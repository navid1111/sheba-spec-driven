"""
MetricsService - Business metrics and analytics for operations dashboard.

Provides aggregated metrics for:
- Customer engagement by segment (new, repeat, inactive)
- Booking conversion from AI outreach
- Worker performance trends (ratings, punctuality, workload)
- Satisfaction and turnover indicators
- Burnout alerts

Used by: Admin dashboard endpoints (FR-009)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, func, and_, or_, case, cast, Integer
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.logging import get_logger
from src.models.users import User, UserType
from src.models.workers import Worker
from src.models.customers import Customer
from src.models.bookings import Booking, BookingStatus
from src.models.reviews import Review
from src.models.ai_messages import AIMessage, MessageChannel, MessageType, DeliveryStatus
from src.models.user_activity_events import UserActivityEvent, EventType


logger = get_logger(__name__)


class MetricsService:
    """
    Service for calculating business metrics and analytics.
    
    Provides aggregate data for operations dashboard, including:
    - Customer segmentation and engagement rates
    - AI outreach effectiveness (conversion rates)
    - Worker performance trends
    - Quality and satisfaction metrics
    - Burnout risk indicators
    """
    
    def __init__(self, db: Session):
        """
        Initialize MetricsService.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("MetricsService initialized")
    
    def get_overview_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get high-level overview metrics for dashboard.
        
        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: now)
            
        Returns:
            {
                'engagement': {...},  # Customer engagement by segment
                'conversions': {...},  # Booking conversion from outreach
                'workers': {...},  # Worker performance summary
                'alerts': {...},  # Active alerts count
                'period': {'start': ..., 'end': ...}
            }
        """
        # Default to last 30 days
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        logger.info(
            f"Calculating overview metrics",
            extra={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }
        )
        
        # Calculate each metric category
        engagement = self.get_engagement_by_segment(start_date, end_date)
        conversions = self.get_conversion_metrics(start_date, end_date)
        workers = self.get_worker_performance_summary(start_date, end_date)
        alerts = self.get_active_alerts_count()
        
        return {
            'engagement': engagement,
            'conversions': conversions,
            'workers': workers,
            'alerts': alerts,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
            }
        }
    
    def get_engagement_by_segment(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate customer engagement rates by segment.
        
        Segments:
        - New: First booking < 30 days ago
        - Repeat: 2+ bookings, last booking < 30 days ago
        - Inactive: Last booking > 30 days ago
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            {
                'total_customers': int,
                'new': {'count': int, 'engagement_rate': float},
                'repeat': {'count': int, 'engagement_rate': float},
                'inactive': {'count': int, 'engagement_rate': float},
            }
        """
        # Get all customers
        stmt = select(func.count(Customer.id))
        total_customers = self.db.execute(stmt).scalar() or 0
        
        # New customers (first booking in last 30 days)
        cutoff_30_days = datetime.now(timezone.utc) - timedelta(days=30)
        
        stmt_new = (
            select(func.count(func.distinct(Booking.customer_id)))
            .where(
                and_(
                    Booking.created_at >= cutoff_30_days,
                    Booking.created_at.between(start_date, end_date),
                )
            )
        )
        new_count = self.db.execute(stmt_new).scalar() or 0
        
        # Repeat customers (2+ bookings, recent activity)
        stmt_repeat = (
            select(func.count(func.distinct(Booking.customer_id)))
            .select_from(Booking)
            .group_by(Booking.customer_id)
            .having(func.count(Booking.id) >= 2)
            .where(Booking.created_at >= cutoff_30_days)
        )
        repeat_count = len(self.db.execute(stmt_repeat).all())
        
        # Inactive customers (last booking > 30 days ago)
        stmt_inactive = (
            select(func.count(func.distinct(Booking.customer_id)))
            .where(
                and_(
                    Booking.created_at < cutoff_30_days,
                    Booking.customer_id.notin_(
                        select(Booking.customer_id)
                        .where(Booking.created_at >= cutoff_30_days)
                    )
                )
            )
        )
        inactive_count = self.db.execute(stmt_inactive).scalar() or 0
        
        # Calculate engagement rates (bookings in period / total in segment)
        # For simplicity, use booking count as engagement proxy
        def calc_engagement_rate(segment_count):
            if total_customers == 0:
                return 0.0
            return round((segment_count / total_customers) * 100, 2)
        
        return {
            'total_customers': total_customers,
            'new': {
                'count': new_count,
                'engagement_rate': calc_engagement_rate(new_count),
            },
            'repeat': {
                'count': repeat_count,
                'engagement_rate': calc_engagement_rate(repeat_count),
            },
            'inactive': {
                'count': inactive_count,
                'engagement_rate': calc_engagement_rate(inactive_count),
            },
        }
    
    def get_conversion_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate booking conversion rates from AI outreach.
        
        Tracks:
        - Messages sent (SmartEngage reminders)
        - Click-through rate (deeplink followed events)
        - Booking conversion rate (bookings with correlation_id)
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            {
                'messages_sent': int,
                'clicks': int,
                'click_rate': float,  # %
                'bookings': int,
                'conversion_rate': float,  # %
            }
        """
        # Count SmartEngage messages sent
        stmt_sent = (
            select(func.count(AIMessage.id))
            .where(
                and_(
                    AIMessage.agent_type == 'smartengage',
                    AIMessage.message_type == MessageType.REMINDER,
                    AIMessage.delivery_status == DeliveryStatus.SENT,
                    AIMessage.sent_at.between(start_date, end_date),
                )
            )
        )
        messages_sent = self.db.execute(stmt_sent).scalar() or 0
        
        # Count deeplink clicks
        stmt_clicks = (
            select(func.count(UserActivityEvent.id))
            .where(
                and_(
                    UserActivityEvent.event_type == EventType.DEEPLINK_FOLLOWED,
                    UserActivityEvent.occurred_at.between(start_date, end_date),
                )
            )
        )
        clicks = self.db.execute(stmt_clicks).scalar() or 0
        
        # Count bookings with correlation_id (from AI outreach)
        # Note: Requires bookings table to have correlation_id or metadata tracking
        # For now, count bookings created after message send within 48h window
        stmt_conversions = (
            select(func.count(func.distinct(Booking.id)))
            .select_from(AIMessage)
            .join(
                Booking,
                and_(
                    Booking.customer_id == AIMessage.user_id,
                    Booking.created_at >= AIMessage.sent_at,
                    Booking.created_at <= AIMessage.sent_at + timedelta(hours=48),
                )
            )
            .where(
                and_(
                    AIMessage.agent_type == 'smartengage',
                    AIMessage.delivery_status == DeliveryStatus.SENT,
                    AIMessage.sent_at.between(start_date, end_date),
                )
            )
        )
        bookings = self.db.execute(stmt_conversions).scalar() or 0
        
        # Calculate rates
        click_rate = round((clicks / messages_sent * 100), 2) if messages_sent > 0 else 0.0
        conversion_rate = round((bookings / messages_sent * 100), 2) if messages_sent > 0 else 0.0
        
        return {
            'messages_sent': messages_sent,
            'clicks': clicks,
            'click_rate': click_rate,
            'bookings': bookings,
            'conversion_rate': conversion_rate,
        }
    
    def get_worker_performance_summary(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate aggregate worker performance metrics.
        
        Includes:
        - Total active workers
        - Average rating
        - Punctuality rate
        - Coaching sent count
        - High/low performers
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            {
                'total_workers': int,
                'average_rating': float,
                'punctuality_rate': float,  # %
                'coaching_sent': int,
                'high_performers': int,  # Rating >= 4.5
                'low_performers': int,  # Rating < 3.5
                'at_risk_count': int,  # Burnout risk
            }
        """
        # Total active workers (have bookings in period)
        stmt_total = (
            select(func.count(func.distinct(Booking.worker_id)))
            .where(Booking.created_at.between(start_date, end_date))
        )
        total_workers = self.db.execute(stmt_total).scalar() or 0
        
        # Average rating across all workers
        stmt_rating = (
            select(func.avg(Review.rating))
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(Booking.created_at.between(start_date, end_date))
        )
        average_rating = self.db.execute(stmt_rating).scalar() or 0.0
        average_rating = round(float(average_rating), 2)
        
        # Punctuality rate (placeholder - would need actual punctuality data)
        # For now, estimate from review data or booking status
        punctuality_rate = 85.0  # Placeholder
        
        # Coaching sent count
        stmt_coaching = (
            select(func.count(AIMessage.id))
            .where(
                and_(
                    AIMessage.agent_type == 'coachnova',
                    AIMessage.delivery_status == DeliveryStatus.SENT,
                    AIMessage.sent_at.between(start_date, end_date),
                )
            )
        )
        coaching_sent = self.db.execute(stmt_coaching).scalar() or 0
        
        # High performers (avg rating >= 4.5)
        stmt_high = (
            select(func.count(func.distinct(Booking.worker_id)))
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(Booking.created_at.between(start_date, end_date))
            .group_by(Booking.worker_id)
            .having(func.avg(Review.rating) >= 4.5)
        )
        high_performers = len(self.db.execute(stmt_high).all())
        
        # Low performers (avg rating < 3.5)
        stmt_low = (
            select(func.count(func.distinct(Booking.worker_id)))
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(Booking.created_at.between(start_date, end_date))
            .group_by(Booking.worker_id)
            .having(func.avg(Review.rating) < 3.5)
        )
        low_performers = len(self.db.execute(stmt_low).all())
        
        # At-risk count (placeholder - would need workload data)
        at_risk_count = 0
        
        return {
            'total_workers': total_workers,
            'average_rating': average_rating,
            'punctuality_rate': punctuality_rate,
            'coaching_sent': coaching_sent,
            'high_performers': high_performers,
            'low_performers': low_performers,
            'at_risk_count': at_risk_count,
        }
    
    def get_active_alerts_count(self) -> Dict[str, int]:
        """
        Get count of active alerts by type.
        
        Returns:
            {
                'burnout': int,  # Workers at burnout risk
                'low_rating': int,  # Workers with low ratings
                'high_absence': int,  # Workers with high absence rate
                'total': int,
            }
        """
        # Placeholder - would integrate with alerting_service
        # For now, return zeros
        return {
            'burnout': 0,
            'low_rating': 0,
            'high_absence': 0,
            'total': 0,
        }
    
    def get_rating_distribution(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[int, int]:
        """
        Get distribution of ratings (1-5 stars).
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            {1: count, 2: count, 3: count, 4: count, 5: count}
        """
        stmt = (
            select(
                Review.rating,
                func.count(Review.id).label('count')
            )
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(Booking.created_at.between(start_date, end_date))
            .group_by(Review.rating)
        )
        
        results = self.db.execute(stmt).all()
        
        # Initialize all ratings to 0
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for rating, count in results:
            if rating in distribution:
                distribution[rating] = count
        
        return distribution
    
    def get_satisfaction_trend(
        self,
        days: int = 30,
        interval_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Get satisfaction (rating) trend over time.
        
        Args:
            days: Number of days to look back
            interval_days: Days per data point
            
        Returns:
            [
                {'date': '2025-10-01', 'avg_rating': 4.2, 'review_count': 45},
                ...
            ]
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Group by interval_days periods
        trend_data = []
        current_start = start_date
        
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=interval_days), end_date)
            
            stmt_avg = (
                select(
                    func.avg(Review.rating).label('avg_rating'),
                    func.count(Review.id).label('review_count')
                )
                .select_from(Review)
                .join(Booking, Review.booking_id == Booking.id)
                .where(Booking.created_at.between(current_start, current_end))
            )
            
            result = self.db.execute(stmt_avg).one()
            avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
            review_count = result.review_count or 0
            
            trend_data.append({
                'date': current_start.date().isoformat(),
                'avg_rating': round(avg_rating, 2),
                'review_count': review_count,
            })
            
            current_start = current_end
        
        return trend_data


# Factory function
def get_metrics_service(db: Session) -> MetricsService:
    """
    Get MetricsService instance.
    
    Args:
        db: Database session
        
    Returns:
        MetricsService instance
    """
    return MetricsService(db)
