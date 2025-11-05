"""
Performance Service for analyzing worker performance metrics.

Queries worker_performance_snapshots to calculate eligibility for coaching interventions.
Used by CoachNova to determine if workers need performance coaching.
"""
from typing import Dict, Optional, Any
from uuid import UUID
from datetime import datetime, timezone, date as date_type
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workers import WorkerPerformanceSnapshot
from src.lib.logging import get_logger

logger = get_logger(__name__)


# Eligibility thresholds (from spec requirements)
LATE_ARRIVALS_THRESHOLD = 3  # >= 3 late arrivals in last 7 days triggers coaching
LOW_RATING_THRESHOLD = 3.5  # < 3.5 average rating triggers coaching
HIGH_WORKLOAD_THRESHOLD = 80  # >= 80 workload score triggers burnout coaching
HIGH_BURNOUT_THRESHOLD = 70  # >= 70 burnout score triggers intervention


class PerformanceService:
    """Service for analyzing worker performance and determining coaching eligibility."""
    
    @staticmethod
    async def get_signals(
        worker_id: UUID,
        db: AsyncSession,
        snapshot_date: Optional[date_type] = None
    ) -> Dict[str, Any]:
        """
        Get performance signals for a worker from latest snapshot.
        
        Args:
            worker_id: UUID of the worker
            db: Database session (async)
            snapshot_date: Optional specific date to query (default: latest)
            
        Returns:
            Dictionary with performance signals:
            {
                'worker_id': UUID,
                'snapshot_date': date,
                'late_arrivals_last_7_days': int,
                'avg_rating_last_30_days': float | None,
                'jobs_completed_last_7_days': int,
                'cancellations_by_worker': int,
                'hours_worked_last_7_days': float,
                'workload_score': int,
                'burnout_score': int,
                'has_performance_issues': bool,
                'eligible_for_coaching': bool,
                'issues': list[str]  # e.g., ['late_arrivals', 'low_rating']
            }
            
        Raises:
            ValueError: If no performance snapshot found for worker
        """
        logger.info(
            f"Fetching performance signals for worker",
            extra={"worker_id": str(worker_id)}
        )
        
        # Query for latest snapshot (or specific date)
        stmt = select(WorkerPerformanceSnapshot).where(
            WorkerPerformanceSnapshot.worker_id == worker_id
        )
        
        if snapshot_date:
            stmt = stmt.where(WorkerPerformanceSnapshot.date == snapshot_date)
        else:
            # Get most recent snapshot
            stmt = stmt.order_by(desc(WorkerPerformanceSnapshot.date)).limit(1)
        
        result = await db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        
        if not snapshot:
            logger.warning(
                f"No performance snapshot found for worker",
                extra={"worker_id": str(worker_id)}
            )
            raise ValueError(f"No performance snapshot found for worker {worker_id}")
        
        # Analyze performance issues
        issues = []
        
        if snapshot.late_arrivals_last_7_days >= LATE_ARRIVALS_THRESHOLD:
            issues.append('late_arrivals')
        
        if snapshot.avg_rating_last_30_days and snapshot.avg_rating_last_30_days < LOW_RATING_THRESHOLD:
            issues.append('low_rating')
        
        if snapshot.workload_score >= HIGH_WORKLOAD_THRESHOLD:
            issues.append('high_workload')
        
        if snapshot.burnout_score >= HIGH_BURNOUT_THRESHOLD:
            issues.append('burnout_risk')
        
        has_issues = len(issues) > 0
        
        # Eligibility: has at least one performance issue
        eligible = has_issues
        
        logger.info(
            f"Performance analysis complete",
            extra={
                "worker_id": str(worker_id),
                "snapshot_date": str(snapshot.date),
                "late_arrivals": snapshot.late_arrivals_last_7_days,
                "avg_rating": float(snapshot.avg_rating_last_30_days) if snapshot.avg_rating_last_30_days else None,
                "workload_score": snapshot.workload_score,
                "burnout_score": snapshot.burnout_score,
                "has_issues": has_issues,
                "eligible": eligible,
                "issues": issues,
            }
        )
        
        return {
            'worker_id': worker_id,
            'snapshot_date': snapshot.date,
            'late_arrivals_last_7_days': snapshot.late_arrivals_last_7_days,
            'avg_rating_last_30_days': float(snapshot.avg_rating_last_30_days) if snapshot.avg_rating_last_30_days else None,
            'jobs_completed_last_7_days': snapshot.jobs_completed_last_7_days,
            'cancellations_by_worker': snapshot.cancellations_by_worker,
            'hours_worked_last_7_days': float(snapshot.hours_worked_last_7_days),
            'workload_score': snapshot.workload_score,
            'burnout_score': snapshot.burnout_score,
            'has_performance_issues': has_issues,
            'eligible_for_coaching': eligible,
            'issues': issues,
        }
    
    @staticmethod
    def get_signals_sync(
        worker_id: UUID,
        db: Session,
        snapshot_date: Optional[date_type] = None
    ) -> Dict[str, Any]:
        """
        Synchronous version of get_signals for non-async contexts.
        
        Args:
            worker_id: UUID of the worker
            db: Database session (sync)
            snapshot_date: Optional specific date to query (default: latest)
            
        Returns:
            Same as get_signals()
            
        Raises:
            ValueError: If no performance snapshot found for worker
        """
        logger.info(
            f"Fetching performance signals for worker (sync)",
            extra={"worker_id": str(worker_id)}
        )
        
        # Query for latest snapshot (or specific date)
        stmt = select(WorkerPerformanceSnapshot).where(
            WorkerPerformanceSnapshot.worker_id == worker_id
        )
        
        if snapshot_date:
            stmt = stmt.where(WorkerPerformanceSnapshot.date == snapshot_date)
        else:
            # Get most recent snapshot
            stmt = stmt.order_by(desc(WorkerPerformanceSnapshot.date)).limit(1)
        
        result = db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        
        if not snapshot:
            logger.warning(
                f"No performance snapshot found for worker",
                extra={"worker_id": str(worker_id)}
            )
            raise ValueError(f"No performance snapshot found for worker {worker_id}")
        
        # Analyze performance issues
        issues = []
        
        if snapshot.late_arrivals_last_7_days >= LATE_ARRIVALS_THRESHOLD:
            issues.append('late_arrivals')
        
        if snapshot.avg_rating_last_30_days and snapshot.avg_rating_last_30_days < LOW_RATING_THRESHOLD:
            issues.append('low_rating')
        
        if snapshot.workload_score >= HIGH_WORKLOAD_THRESHOLD:
            issues.append('high_workload')
        
        if snapshot.burnout_score >= HIGH_BURNOUT_THRESHOLD:
            issues.append('burnout_risk')
        
        has_issues = len(issues) > 0
        eligible = has_issues
        
        logger.info(
            f"Performance analysis complete (sync)",
            extra={
                "worker_id": str(worker_id),
                "snapshot_date": str(snapshot.date),
                "late_arrivals": snapshot.late_arrivals_last_7_days,
                "avg_rating": float(snapshot.avg_rating_last_30_days) if snapshot.avg_rating_last_30_days else None,
                "workload_score": snapshot.workload_score,
                "burnout_score": snapshot.burnout_score,
                "has_issues": has_issues,
                "eligible": eligible,
                "issues": issues,
            }
        )
        
        return {
            'worker_id': worker_id,
            'snapshot_date': snapshot.date,
            'late_arrivals_last_7_days': snapshot.late_arrivals_last_7_days,
            'avg_rating_last_30_days': float(snapshot.avg_rating_last_30_days) if snapshot.avg_rating_last_30_days else None,
            'jobs_completed_last_7_days': snapshot.jobs_completed_last_7_days,
            'cancellations_by_worker': snapshot.cancellations_by_worker,
            'hours_worked_last_7_days': float(snapshot.hours_worked_last_7_days),
            'workload_score': snapshot.workload_score,
            'burnout_score': snapshot.burnout_score,
            'has_performance_issues': has_issues,
            'eligible_for_coaching': eligible,
            'issues': issues,
        }
