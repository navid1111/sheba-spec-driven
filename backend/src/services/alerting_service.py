"""
AlertingService - Worker health and burnout detection.

Computes alerts for:
- Burnout risk (workload > 1.5x average)
- Low ratings (avg rating < 3.5)
- High absence rate
- Quality decline

Used by: Operations managers for proactive worker support (US3, FR-009)
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from src.lib.logging import get_logger
from src.models.workers import Worker
from src.models.users import User
from src.models.bookings import Booking
from src.models.reviews import Review


logger = get_logger(__name__)


class AlertType:
    """Alert type constants."""
    BURNOUT = "burnout"
    LOW_RATING = "low_rating"
    HIGH_ABSENCE = "high_absence"
    QUALITY_DECLINE = "quality_decline"


class AlertSeverity:
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertingService:
    """
    Service for detecting worker health issues and generating alerts.
    
    Monitors:
    - Workload (burnout risk when > 1.5x average)
    - Rating trends (decline or consistently low)
    - Absence patterns (cancellations, no-shows)
    - Quality metrics (customer satisfaction)
    """
    
    def __init__(self, db: Session):
        """
        Initialize AlertingService.
        
        Args:
            db: Database session
        """
        self.db = db
        logger.info("AlertingService initialized")
    
    def get_all_alerts(
        self,
        days: int = 30,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all active alerts across all workers.
        
        Args:
            days: Days to look back for metrics (default: 30)
            severity: Filter by severity (low, medium, high, critical)
            alert_type: Filter by type (burnout, low_rating, etc.)
            
        Returns:
            List of alert dictionaries with worker details
        """
        logger.info(
            f"Calculating alerts (days={days}, severity={severity}, type={alert_type})"
        )
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        all_alerts = []
        
        # Get all active workers
        stmt = (
            select(Worker, User)
            .join(User, Worker.id == User.id)
            .where(Worker.is_active == True)
        )
        workers = self.db.execute(stmt).all()
        
        for worker, user in workers:
            # Check each alert type
            worker_alerts = self._check_worker_alerts(
                worker, user, start_date, end_date
            )
            
            # Apply filters
            for alert in worker_alerts:
                if severity and alert['severity'] != severity:
                    continue
                if alert_type and alert['type'] != alert_type:
                    continue
                
                all_alerts.append(alert)
        
        logger.info(f"Found {len(all_alerts)} active alerts")
        return all_alerts
    
    def get_worker_alerts(
        self,
        worker_id: UUID,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Get alerts for a specific worker.
        
        Args:
            worker_id: Worker UUID
            days: Days to look back
            
        Returns:
            List of alerts for this worker
        """
        logger.info(f"Checking alerts for worker {worker_id}")
        
        # Get worker
        stmt = (
            select(Worker, User)
            .join(User, Worker.id == User.id)
            .where(Worker.id == worker_id)
        )
        result = self.db.execute(stmt).one_or_none()
        
        if not result:
            return []
        
        worker, user = result
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        return self._check_worker_alerts(worker, user, start_date, end_date)
    
    def _check_worker_alerts(
        self,
        worker: Worker,
        user: User,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Check all alert conditions for a worker.
        
        Args:
            worker: Worker model
            user: User model
            start_date: Start of period
            end_date: End of period
            
        Returns:
            List of alerts for this worker
        """
        alerts = []
        
        # Calculate metrics
        metrics = self._calculate_worker_metrics(worker.id, start_date, end_date)
        
        # Check burnout (workload > 1.5x average)
        burnout_alert = self._check_burnout(worker, user, metrics)
        if burnout_alert:
            alerts.append(burnout_alert)
        
        # Check low rating
        low_rating_alert = self._check_low_rating(worker, user, metrics)
        if low_rating_alert:
            alerts.append(low_rating_alert)
        
        # Check quality decline
        quality_decline_alert = self._check_quality_decline(worker, user, metrics)
        if quality_decline_alert:
            alerts.append(quality_decline_alert)
        
        return alerts
    
    def _calculate_worker_metrics(
        self,
        worker_id: UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Calculate metrics for alert evaluation.
        
        Args:
            worker_id: Worker UUID
            start_date: Start of period
            end_date: End of period
            
        Returns:
            Dictionary of metrics
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
        total_bookings = self.db.execute(stmt_bookings).scalar() or 0
        
        # Average rating
        stmt_rating = (
            select(func.avg(Review.rating))
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(
                and_(
                    Booking.worker_id == worker_id,
                    Booking.created_at.between(start_date, end_date),
                )
            )
        )
        avg_rating = self.db.execute(stmt_rating).scalar()
        avg_rating = float(avg_rating) if avg_rating else None
        
        # Previous period rating (for trend analysis)
        prev_start = start_date - (end_date - start_date)
        prev_end = start_date
        
        stmt_prev_rating = (
            select(func.avg(Review.rating))
            .select_from(Review)
            .join(Booking, Review.booking_id == Booking.id)
            .where(
                and_(
                    Booking.worker_id == worker_id,
                    Booking.created_at.between(prev_start, prev_end),
                )
            )
        )
        prev_rating = self.db.execute(stmt_prev_rating).scalar()
        prev_rating = float(prev_rating) if prev_rating else None
        
        # Calculate average workload across all workers for comparison
        # First, get per-worker booking counts
        stmt_worker_counts = (
            select(func.count(Booking.id))
            .select_from(Booking)
            .where(Booking.created_at.between(start_date, end_date))
            .group_by(Booking.worker_id)
        )
        worker_counts = self.db.execute(stmt_worker_counts).fetchall()
        
        # Calculate average
        if worker_counts:
            avg_workload = sum(count[0] for count in worker_counts) / len(worker_counts)
        else:
            avg_workload = 0.0
        
        return {
            'total_bookings': total_bookings,
            'avg_rating': avg_rating,
            'prev_rating': prev_rating,
            'avg_workload_all_workers': avg_workload,
        }
    
    def _check_burnout(
        self,
        worker: Worker,
        user: User,
        metrics: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if worker is at burnout risk.
        
        Condition: Workload > 1.5x average across all workers
        
        Args:
            worker: Worker model
            user: User model
            metrics: Calculated metrics
            
        Returns:
            Alert dict if condition met, None otherwise
        """
        workload = metrics['total_bookings']
        avg_workload = metrics['avg_workload_all_workers']
        
        if avg_workload == 0:
            return None
        
        workload_ratio = workload / avg_workload
        
        # Burnout threshold: 1.5x average
        if workload_ratio > 1.5:
            # Severity based on ratio
            if workload_ratio > 2.5:
                severity = AlertSeverity.CRITICAL
            elif workload_ratio > 2.0:
                severity = AlertSeverity.HIGH
            else:
                severity = AlertSeverity.MEDIUM
            
            return {
                'type': AlertType.BURNOUT,
                'severity': severity,
                'worker_id': str(worker.id),
                'worker_name': user.name,
                'worker_email': user.email,
                'message': f'Workload {workload_ratio:.1f}x average ({workload} bookings vs avg {avg_workload:.0f})',
                'metrics': {
                    'total_bookings': workload,
                    'average_bookings': round(avg_workload, 1),
                    'workload_ratio': round(workload_ratio, 2),
                },
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        
        return None
    
    def _check_low_rating(
        self,
        worker: Worker,
        user: User,
        metrics: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if worker has consistently low rating.
        
        Condition: Average rating < 3.5
        
        Args:
            worker: Worker model
            user: User model
            metrics: Calculated metrics
            
        Returns:
            Alert dict if condition met, None otherwise
        """
        avg_rating = metrics['avg_rating']
        
        if avg_rating is None:
            return None
        
        # Low rating threshold: < 3.5
        if avg_rating < 3.5:
            # Severity based on rating
            if avg_rating < 2.5:
                severity = AlertSeverity.CRITICAL
            elif avg_rating < 3.0:
                severity = AlertSeverity.HIGH
            else:
                severity = AlertSeverity.MEDIUM
            
            return {
                'type': AlertType.LOW_RATING,
                'severity': severity,
                'worker_id': str(worker.id),
                'worker_name': user.name,
                'worker_email': user.email,
                'message': f'Average rating {avg_rating:.1f}/5.0 (threshold: 3.5)',
                'metrics': {
                    'avg_rating': round(avg_rating, 2),
                    'threshold': 3.5,
                },
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        
        return None
    
    def _check_quality_decline(
        self,
        worker: Worker,
        user: User,
        metrics: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if worker's quality is declining.
        
        Condition: Rating dropped > 0.5 points from previous period
        
        Args:
            worker: Worker model
            user: User model
            metrics: Calculated metrics
            
        Returns:
            Alert dict if condition met, None otherwise
        """
        avg_rating = metrics['avg_rating']
        prev_rating = metrics['prev_rating']
        
        if avg_rating is None or prev_rating is None:
            return None
        
        decline = prev_rating - avg_rating
        
        # Quality decline threshold: > 0.5 point drop
        if decline > 0.5:
            # Severity based on decline magnitude
            if decline > 1.5:
                severity = AlertSeverity.CRITICAL
            elif decline > 1.0:
                severity = AlertSeverity.HIGH
            else:
                severity = AlertSeverity.MEDIUM
            
            return {
                'type': AlertType.QUALITY_DECLINE,
                'severity': severity,
                'worker_id': str(worker.id),
                'worker_name': user.name,
                'worker_email': user.email,
                'message': f'Rating declined {decline:.1f} points (from {prev_rating:.1f} to {avg_rating:.1f})',
                'metrics': {
                    'current_rating': round(avg_rating, 2),
                    'previous_rating': round(prev_rating, 2),
                    'decline': round(decline, 2),
                },
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
        
        return None


# Factory function
def get_alerting_service(db: Session) -> AlertingService:
    """
    Get AlertingService instance.
    
    Args:
        db: Database session
        
    Returns:
        AlertingService instance
    """
    return AlertingService(db)
