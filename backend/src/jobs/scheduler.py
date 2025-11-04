"""
Scheduler runner using APScheduler with Postgres advisory locks.

This module provides a singleton scheduler that runs background jobs
using APScheduler. Jobs are coordinated via Postgres advisory locks
stored in the jobs table to prevent concurrent execution.

Usage:
    scheduler = get_scheduler()
    scheduler.start()
    
    # Add a job
    scheduler.add_job(
        my_job_function,
        trigger=CronTrigger(hour=9),
        id="daily_reminder",
        replace_existing=True
    )
"""
import logging
import hashlib
from typing import Optional, Callable
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.db import get_db
from src.models.jobs import Job, JobType, JobStatus

logger = logging.getLogger(__name__)


# Singleton scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def get_lock_key(job_id: str) -> int:
    """
    Generate a consistent integer lock key from job ID for pg_advisory_lock.
    
    Args:
        job_id: Job identifier string
        
    Returns:
        Integer lock key (positive, within bigint range)
    """
    # Hash the job_id and take first 8 bytes as signed int64
    hash_bytes = hashlib.sha256(job_id.encode()).digest()[:8]
    lock_key = int.from_bytes(hash_bytes, byteorder='big', signed=False)
    # Convert to signed int64 range (Postgres bigint)
    if lock_key > 2**63 - 1:
        lock_key = lock_key - 2**64
    return abs(lock_key)  # Use positive values for simplicity


async def try_acquire_lock(db: AsyncSession, lock_key: int) -> bool:
    """
    Try to acquire Postgres advisory lock.
    
    Args:
        db: Database session
        lock_key: Integer lock key
        
    Returns:
        True if lock acquired, False otherwise
    """
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(:lock_key)"),
        {"lock_key": lock_key}
    )
    acquired = result.scalar()
    return bool(acquired)


async def release_lock(db: AsyncSession, lock_key: int) -> None:
    """
    Release Postgres advisory lock.
    
    Args:
        db: Database session
        lock_key: Integer lock key
    """
    await db.execute(
        text("SELECT pg_advisory_unlock(:lock_key)"),
        {"lock_key": lock_key}
    )


def with_advisory_lock(job_id: str, job_type: JobType = JobType.OTHER):
    """
    Decorator to wrap a job function with Postgres advisory lock.
    
    This ensures only one instance of the job runs at a time across
    multiple scheduler instances.
    
    Args:
        job_id: Unique job identifier
        job_type: Job type enum value
        
    Example:
        @with_advisory_lock("daily_snapshot", JobType.SNAPSHOT_DAILY)
        async def daily_snapshot_job():
            # Job logic here
            pass
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            lock_key = get_lock_key(job_id)
            
            async for db in get_db():
                try:
                    # Try to acquire lock
                    acquired = await try_acquire_lock(db, lock_key)
                    
                    if not acquired:
                        logger.info(
                            f"Job {job_id} already running (lock {lock_key}), skipping"
                        )
                        return
                    
                    logger.info(f"Job {job_id} acquired lock {lock_key}, executing")
                    
                    # Create/update job record
                    from src.models.jobs import Job
                    from sqlalchemy import select
                    
                    stmt = select(Job).where(Job.lock_key == lock_key)
                    result = await db.execute(stmt)
                    job_record = result.scalar_one_or_none()
                    
                    if not job_record:
                        job_record = Job(
                            type=job_type,
                            scheduled_for=datetime.now(timezone.utc),
                            status=JobStatus.PROCESSING,
                            attempts=1,
                            lock_key=lock_key,
                        )
                        db.add(job_record)
                    else:
                        job_record.status = JobStatus.PROCESSING
                        job_record.run_at = datetime.now(timezone.utc)
                        job_record.attempts += 1
                    
                    await db.commit()
                    
                    # Execute job
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Mark as done
                        job_record.status = JobStatus.DONE
                        await db.commit()
                        
                        logger.info(f"Job {job_id} completed successfully")
                        return result
                        
                    except Exception as e:
                        # Mark as failed
                        job_record.status = JobStatus.FAILED
                        await db.commit()
                        
                        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
                        raise
                    
                finally:
                    # Always release lock
                    await release_lock(db, lock_key)
                    logger.info(f"Job {job_id} released lock {lock_key}")
                    
        return wrapper
    return decorator


class SchedulerManager:
    """
    Manager for APScheduler with lifecycle management.
    """
    
    def __init__(self):
        """Initialize scheduler manager."""
        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                'coalesce': True,  # Combine missed runs
                'max_instances': 1,  # Only one instance per job
                'misfire_grace_time': 300,  # 5 minutes grace period
            }
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )
        
        logger.info("SchedulerManager initialized")
    
    def _on_job_executed(self, event):
        """Handle job execution event."""
        logger.info(
            f"Job {event.job_id} executed successfully "
            f"(runtime: {event.retval})"
        )
    
    def _on_job_error(self, event):
        """Handle job error event."""
        logger.error(
            f"Job {event.job_id} raised {event.exception.__class__.__name__}: "
            f"{event.exception}",
            exc_info=event.exception
        )
    
    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
        else:
            logger.warning("Scheduler already running")
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler.
        
        Args:
            wait: Whether to wait for running jobs to finish
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")
        else:
            logger.warning("Scheduler not running")
    
    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        day_of_week: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Add a cron-scheduled job.
        
        Args:
            func: Job function (should be decorated with @with_advisory_lock)
            job_id: Unique job identifier
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            day_of_week: Day of week (mon,tue,wed,thu,fri,sat,sun)
            **kwargs: Additional APScheduler job options
        """
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            timezone="UTC"
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(f"Added cron job: {job_id} (hour={hour}, minute={minute})")
    
    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        seconds: Optional[int] = None,
        minutes: Optional[int] = None,
        hours: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        Add an interval-scheduled job.
        
        Args:
            func: Job function (should be decorated with @with_advisory_lock)
            job_id: Unique job identifier
            seconds: Interval in seconds
            minutes: Interval in minutes
            hours: Interval in hours
            **kwargs: Additional APScheduler job options
        """
        # Ensure at least one interval is specified
        if not any([seconds, minutes, hours]):
            raise ValueError("At least one of seconds, minutes, or hours must be specified")
        
        trigger = IntervalTrigger(
            seconds=seconds or 0,
            minutes=minutes or 0,
            hours=hours or 0,
            timezone="UTC"
        )
        
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(
            f"Added interval job: {job_id} "
            f"(seconds={seconds}, minutes={minutes}, hours={hours})"
        )
    
    def remove_job(self, job_id: str) -> None:
        """
        Remove a scheduled job.
        
        Args:
            job_id: Job identifier
        """
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")
    
    def get_jobs(self) -> list:
        """Get list of scheduled jobs."""
        return self.scheduler.get_jobs()


def get_scheduler() -> SchedulerManager:
    """
    Get singleton scheduler instance.
    
    Returns:
        SchedulerManager instance
    """
    global _scheduler
    
    if _scheduler is None:
        _scheduler = SchedulerManager()
    
    return _scheduler
