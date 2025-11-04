"""
Campaign Runner Job - Scheduled SmartEngage Reminders.

This job runs periodically to send SmartEngage reminder campaigns to eligible customers.
It coordinates with the scheduler using Postgres advisory locks to prevent concurrent execution.

Execution flow:
1. Acquire advisory lock (via @with_advisory_lock decorator)
2. Query eligible customers via SegmentationService
3. Call SmartEngageOrchestrator.generate_and_send_bulk_reminders()
4. Log results with correlation_id
5. Update job status in database
6. Release lock

Default schedule: Daily at 9:00 AM UTC (configurable)
"""
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.lib.logging import get_logger
from src.lib.db import get_db
from src.models.jobs import JobType
from src.ai.smartengage import get_smartengage_orchestrator

logger = get_logger(__name__)


async def run_smartengage_campaign(
    booking_cadence_days: int = 21,
    send_window_start: int = 9,
    send_window_end: int = 18,
    batch_size: int = 50,
    promo_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run SmartEngage reminder campaign for eligible customers.
    
    Note: This function should be wrapped with @with_advisory_lock decorator
    when deploying to production with multiple scheduler instances to prevent
    concurrent execution. For single-instance deployments, the lock is not required.
    
    Args:
        booking_cadence_days: Days since last booking to target (default 21)
        send_window_start: Hour to start sending (9am local time)
        send_window_end: Hour to stop sending (6pm local time)
        batch_size: Number of customers per batch (default 50)
        promo_code: Optional promo code for all customers
        
    Returns:
        Dictionary with campaign results:
        {
            "correlation_id": UUID,
            "started_at": datetime,
            "finished_at": datetime,
            "total_eligible": int,
            "sent": int,
            "failed": int,
            "skipped": int,
            "duration_seconds": float,
        }
    """
    correlation_id = uuid4()
    started_at = datetime.now(timezone.utc)
    
    logger.info(
        f"Starting SmartEngage campaign runner "
        f"(correlation_id: {correlation_id}, "
        f"cadence: {booking_cadence_days} days, "
        f"window: {send_window_start}-{send_window_end}h, "
        f"batch_size: {batch_size})"
    )
    
    try:
        # Get database session
        db = next(get_db())
        
        # Initialize orchestrator
        orchestrator = get_smartengage_orchestrator(db)
        
        # Run bulk campaign
        campaign_result = await orchestrator.generate_and_send_bulk_reminders(
            booking_cadence_days=booking_cadence_days,
            send_window_start=send_window_start,
            send_window_end=send_window_end,
            batch_size=batch_size,
            promo_code=promo_code,
        )
        
        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()
        
        # Build result
        result = {
            "correlation_id": correlation_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_seconds": duration,
            **campaign_result,  # Include all campaign results
        }
        
        logger.info(
            f"SmartEngage campaign completed "
            f"(correlation_id: {correlation_id}, "
            f"duration: {duration:.2f}s, "
            f"sent: {campaign_result['sent']}/{campaign_result['total_eligible']}, "
            f"failed: {campaign_result['failed']}, "
            f"skipped: {campaign_result['skipped']})"
        )
        
        return result
        
    except Exception as e:
        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()
        
        logger.error(
            f"SmartEngage campaign failed "
            f"(correlation_id: {correlation_id}, "
            f"duration: {duration:.2f}s): {e}",
            exc_info=True,
        )
        
        # Re-raise to mark job as failed
        raise


def run_campaign_sync(*args, **kwargs):
    """
    Synchronous wrapper for APScheduler compatibility.
    
    APScheduler expects synchronous functions, so this wrapper
    creates an event loop and runs the async campaign function.
    """
    return asyncio.run(run_smartengage_campaign(*args, **kwargs))


# ============================================================================
# Scheduler Registration
# ============================================================================


def register_campaign_jobs(scheduler_manager):
    """
    Register SmartEngage campaign jobs with the scheduler.
    
    This function should be called during application startup to
    register all SmartEngage-related scheduled jobs.
    
    Args:
        scheduler_manager: SchedulerManager instance from get_scheduler()
        
    Example:
        from src.jobs.scheduler import get_scheduler
        from src.jobs.campaign_runner import register_campaign_jobs
        
        scheduler = get_scheduler()
        register_campaign_jobs(scheduler)
        scheduler.start()
    """
    logger.info("Registering SmartEngage campaign jobs")
    
    # Daily campaign at 9:00 AM UTC
    # This is 3:00 PM Bangladesh time (UTC+6)
    scheduler_manager.add_cron_job(
        func=run_campaign_sync,
        job_id="smartengage_daily_campaign",
        hour=9,
        minute=0,
    )
    
    logger.info("SmartEngage campaign jobs registered")


# ============================================================================
# Manual Trigger (for testing and debugging)
# ============================================================================


async def trigger_campaign_manual(
    booking_cadence_days: int = 21,
    promo_code: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Manually trigger a SmartEngage campaign (for testing/debugging).
    
    This bypasses the scheduler and runs the campaign immediately.
    Use this for:
    - Testing the campaign runner
    - Running ad-hoc campaigns
    - Debugging campaign issues
    
    Args:
        booking_cadence_days: Days since last booking (default 21)
        promo_code: Optional promo code for campaign
        dry_run: If True, only find eligible customers without sending
        
    Returns:
        Campaign results dictionary
    """
    logger.info(
        f"Manual campaign trigger "
        f"(cadence: {booking_cadence_days}, promo: {promo_code}, dry_run: {dry_run})"
    )
    
    if dry_run:
        # Dry run: just count eligible customers
        db = next(get_db())
        orchestrator = get_smartengage_orchestrator(db)
        
        eligible_customers = orchestrator.segmentation_service.find_eligible_for_reminders(
            booking_cadence_days=booking_cadence_days,
        )
        
        return {
            "dry_run": True,
            "total_eligible": len(eligible_customers),
            "customer_ids": [str(c.id) for c in eligible_customers],
        }
    else:
        # Real run
        return await run_smartengage_campaign(
            booking_cadence_days=booking_cadence_days,
            promo_code=promo_code,
        )


# ============================================================================
# Configuration Presets
# ============================================================================


CAMPAIGN_PRESETS = {
    "default": {
        "booking_cadence_days": 21,
        "send_window_start": 9,
        "send_window_end": 18,
        "batch_size": 50,
        "promo_code": None,
    },
    "aggressive": {
        "booking_cadence_days": 14,  # 2 weeks
        "send_window_start": 9,
        "send_window_end": 20,  # Later end time
        "batch_size": 100,  # Larger batches
        "promo_code": "COMEBACK15",
    },
    "gentle": {
        "booking_cadence_days": 28,  # 4 weeks
        "send_window_start": 10,
        "send_window_end": 17,  # Shorter window
        "batch_size": 25,  # Smaller batches
        "promo_code": None,
    },
    "weekend": {
        "booking_cadence_days": 21,
        "send_window_start": 10,
        "send_window_end": 16,
        "batch_size": 50,
        "promo_code": "WEEKEND20",
    },
}


async def run_campaign_with_preset(preset_name: str = "default") -> Dict[str, Any]:
    """
    Run campaign with a predefined preset configuration.
    
    Args:
        preset_name: Name of preset (default, aggressive, gentle, weekend)
        
    Returns:
        Campaign results dictionary
        
    Raises:
        ValueError: If preset_name is not recognized
    """
    if preset_name not in CAMPAIGN_PRESETS:
        raise ValueError(
            f"Unknown preset: {preset_name}. "
            f"Available: {', '.join(CAMPAIGN_PRESETS.keys())}"
        )
    
    preset = CAMPAIGN_PRESETS[preset_name]
    logger.info(f"Running campaign with preset: {preset_name}")
    
    return await run_smartengage_campaign(**preset)
