"""
Tests for scheduler with advisory locks.
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.jobs.scheduler import (
    get_scheduler,
    get_lock_key,
    try_acquire_lock,
    release_lock,
    with_advisory_lock,
    SchedulerManager,
)
from src.models.jobs import Job, JobType, JobStatus


@pytest.mark.unit
def test_get_lock_key_consistent():
    """Test that get_lock_key generates consistent keys."""
    job_id = "test_job"
    
    key1 = get_lock_key(job_id)
    key2 = get_lock_key(job_id)
    
    assert key1 == key2
    assert isinstance(key1, int)
    assert key1 > 0  # Positive integer


@pytest.mark.unit
def test_get_lock_key_unique():
    """Test that different job IDs generate different keys."""
    key1 = get_lock_key("job_1")
    key2 = get_lock_key("job_2")
    
    assert key1 != key2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_acquire_lock_success(mock_db_session):
    """Test acquiring advisory lock successfully."""
    # Mock successful lock acquisition
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    
    acquired = await try_acquire_lock(mock_db_session, 12345)
    
    assert acquired is True
    mock_db_session.execute.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_try_acquire_lock_failure(mock_db_session):
    """Test failing to acquire advisory lock."""
    # Mock failed lock acquisition (already held)
    mock_result = MagicMock()
    mock_result.scalar.return_value = False
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    
    acquired = await try_acquire_lock(mock_db_session, 12345)
    
    assert acquired is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_release_lock(mock_db_session):
    """Test releasing advisory lock."""
    mock_db_session.execute = AsyncMock()
    
    await release_lock(mock_db_session, 12345)
    
    mock_db_session.execute.assert_called_once()


@pytest.mark.unit
def test_scheduler_manager_initialization():
    """Test SchedulerManager initialization."""
    manager = SchedulerManager()
    
    assert manager.scheduler is not None
    assert not manager.scheduler.running


@pytest.mark.unit
def test_scheduler_manager_start_stop():
    """Test starting and stopping scheduler."""
    manager = SchedulerManager()
    
    # Start
    manager.start()
    assert manager.scheduler.running
    
    # Shutdown
    manager.shutdown(wait=False)
    assert not manager.scheduler.running


@pytest.mark.unit
def test_scheduler_manager_add_cron_job():
    """Test adding cron job to scheduler."""
    manager = SchedulerManager()
    
    def test_job():
        pass
    
    manager.add_cron_job(
        test_job,
        job_id="test_cron",
        hour=9,
        minute=0
    )
    
    jobs = manager.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "test_cron"
    assert isinstance(jobs[0].trigger, CronTrigger)


@pytest.mark.unit
def test_scheduler_manager_add_interval_job():
    """Test adding interval job to scheduler."""
    manager = SchedulerManager()
    
    def test_job():
        pass
    
    manager.add_interval_job(
        test_job,
        job_id="test_interval",
        minutes=5
    )
    
    jobs = manager.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "test_interval"
    assert isinstance(jobs[0].trigger, IntervalTrigger)


@pytest.mark.unit
def test_scheduler_manager_remove_job():
    """Test removing job from scheduler."""
    manager = SchedulerManager()
    
    def test_job():
        pass
    
    manager.add_interval_job(
        test_job,
        job_id="test_remove",
        minutes=5
    )
    
    assert len(manager.get_jobs()) == 1
    
    manager.remove_job("test_remove")
    
    assert len(manager.get_jobs()) == 0


@pytest.mark.unit
def test_get_scheduler_singleton():
    """Test that get_scheduler returns singleton."""
    scheduler1 = get_scheduler()
    scheduler2 = get_scheduler()
    
    assert scheduler1 is scheduler2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_advisory_lock_decorator_success(mock_db_session):
    """Test advisory lock decorator with successful execution."""
    # Mock lock acquisition
    mock_result = MagicMock()
    mock_result.scalar.return_value = True
    mock_result.scalar_one_or_none.return_value = None
    
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    mock_db_session.commit = AsyncMock()
    mock_db_session.add = MagicMock()
    
    # Mock get_db to yield our mock session
    async def mock_get_db():
        yield mock_db_session
    
    # Create decorated function
    @with_advisory_lock("test_job", JobType.OTHER)
    async def test_job():
        return "success"
    
    # Patch get_db
    with patch('src.jobs.scheduler.get_db', mock_get_db):
        result = await test_job()
    
    assert result == "success"
    assert mock_db_session.commit.call_count >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_advisory_lock_decorator_already_running(mock_db_session):
    """Test advisory lock decorator when lock already held."""
    # Mock failed lock acquisition
    mock_result = MagicMock()
    mock_result.scalar.return_value = False
    
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    
    # Mock get_db to yield our mock session
    async def mock_get_db():
        yield mock_db_session
    
    # Create decorated function
    call_count = 0
    
    @with_advisory_lock("test_job", JobType.OTHER)
    async def test_job():
        nonlocal call_count
        call_count += 1
        return "should not execute"
    
    # Patch get_db
    with patch('src.jobs.scheduler.get_db', mock_get_db):
        result = await test_job()
    
    # Function should not execute when lock not acquired
    assert result is None
    assert call_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_advisory_lock_decorator_handles_exception(mock_db_session):
    """Test advisory lock decorator handles job exceptions."""
    # Mock lock acquisition
    mock_result_lock = MagicMock()
    mock_result_lock.scalar.return_value = True
    
    mock_result_job = MagicMock()
    mock_result_job.scalar_one_or_none.return_value = None
    
    call_count = 0
    
    async def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # First call is lock acquisition
            return mock_result_lock
        else:  # Second call is job query
            return mock_result_job
    
    mock_db_session.execute = AsyncMock(side_effect=mock_execute)
    mock_db_session.commit = AsyncMock()
    mock_db_session.add = MagicMock()
    
    # Mock get_db to yield our mock session
    async def mock_get_db():
        yield mock_db_session
    
    # Create decorated function that raises exception
    @with_advisory_lock("test_job", JobType.OTHER)
    async def test_job():
        raise ValueError("Test error")
    
    # Patch get_db
    with patch('src.jobs.scheduler.get_db', mock_get_db):
        with pytest.raises(ValueError, match="Test error"):
            await test_job()
    
    # Lock should still be released
    assert mock_db_session.execute.call_count >= 3  # acquire + query + release


@pytest.mark.unit
def test_scheduler_manager_event_listeners():
    """Test scheduler event listeners are registered."""
    manager = SchedulerManager()
    
    # Check that listeners are registered
    listeners = manager.scheduler._listeners
    assert len(listeners) > 0


# Fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    return session
