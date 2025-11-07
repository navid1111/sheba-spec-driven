"""
Unit tests for worker coaching consent checks.

Tests the specialized consent functions for CoachNova worker coaching:
- check_worker_coaching_consent()
- check_worker_voice_consent()
- update_worker_coaching_consent()
"""
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from src.lib.consent import (
    check_worker_coaching_consent,
    check_worker_voice_consent,
    update_worker_coaching_consent,
)
from src.models.users import User, UserType
from src.models.workers import Worker


@pytest.mark.asyncio
async def test_check_worker_coaching_consent_opted_in(async_db_session):
    """Test coaching consent check for worker who has opted in."""
    worker_id = uuid4()
    
    # Create user with coaching_enabled = True
    user = User(
        id=worker_id,
        phone_number="+8801712345678",
        user_type=UserType.WORKER,
        name="Test Worker",
        consent={
            "coaching_enabled": True,
            "sms": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    )
    async_db_session.add(user)
    
    # Create worker profile
    worker = Worker(
        id=worker_id,
        skills=["cleaning"],
        service_zones=["dhaka_north"],
    )
    async_db_session.add(worker)
    await async_db_session.commit()
    
    # Check consent
    has_consent = await check_worker_coaching_consent(async_db_session, worker_id)
    assert has_consent is True


@pytest.mark.asyncio
async def test_check_worker_coaching_consent_opted_out(async_db_session):
    """Test coaching consent check for worker who has opted out."""
    worker_id = uuid4()
    
    # Create user with coaching_enabled = False
    user = User(
        id=worker_id,
        phone_number="+8801712345679",
        user_type=UserType.WORKER,
        name="Test Worker 2",
        consent={
            "coaching_enabled": False,
            "sms": True,
        }
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Check consent
    has_consent = await check_worker_coaching_consent(async_db_session, worker_id)
    assert has_consent is False


@pytest.mark.asyncio
async def test_check_worker_coaching_consent_default_false(async_db_session):
    """Test coaching consent defaults to False if not set."""
    worker_id = uuid4()
    
    # Create user without coaching_enabled key
    user = User(
        id=worker_id,
        phone_number="+8801712345680",
        user_type=UserType.WORKER,
        name="Test Worker 3",
        consent={"sms": True}  # No coaching_enabled
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Check consent - should default to False
    has_consent = await check_worker_coaching_consent(async_db_session, worker_id)
    assert has_consent is False


@pytest.mark.asyncio
async def test_check_worker_coaching_consent_worker_not_found(async_db_session):
    """Test coaching consent check for non-existent worker."""
    nonexistent_id = uuid4()
    
    has_consent = await check_worker_coaching_consent(async_db_session, nonexistent_id)
    assert has_consent is False


@pytest.mark.asyncio
async def test_check_worker_voice_consent_opted_in(async_db_session):
    """Test voice consent check for worker who has opted in."""
    worker_id = uuid4()
    
    # Create user
    user = User(
        id=worker_id,
        phone_number="+8801712345681",
        user_type=UserType.WORKER,
        name="Voice Worker",
    )
    async_db_session.add(user)
    
    # Create worker with voice opt-in
    worker = Worker(
        id=worker_id,
        skills=["plumbing"],
        service_zones=["dhaka_south"],
        opt_in_voice=True,
    )
    async_db_session.add(worker)
    await async_db_session.commit()
    
    # Check voice consent
    has_voice = await check_worker_voice_consent(async_db_session, worker_id)
    assert has_voice is True


@pytest.mark.asyncio
async def test_check_worker_voice_consent_opted_out(async_db_session):
    """Test voice consent check for worker who has not opted in."""
    worker_id = uuid4()
    
    # Create user
    user = User(
        id=worker_id,
        phone_number="+8801712345682",
        user_type=UserType.WORKER,
        name="No Voice Worker",
    )
    async_db_session.add(user)
    
    # Create worker with voice opt-in = False
    worker = Worker(
        id=worker_id,
        skills=["electrical"],
        service_zones=["dhaka_central"],
        opt_in_voice=False,
    )
    async_db_session.add(worker)
    await async_db_session.commit()
    
    # Check voice consent
    has_voice = await check_worker_voice_consent(async_db_session, worker_id)
    assert has_voice is False


@pytest.mark.asyncio
async def test_check_worker_voice_consent_default_false(async_db_session):
    """Test voice consent defaults to False if not set."""
    worker_id = uuid4()
    
    # Create user
    user = User(
        id=worker_id,
        phone_number="+8801712345683",
        user_type=UserType.WORKER,
        name="Default Voice Worker",
    )
    async_db_session.add(user)
    
    # Create worker without opt_in_voice (defaults to None/False)
    worker = Worker(
        id=worker_id,
        skills=["carpentry"],
        service_zones=["dhaka_east"],
    )
    async_db_session.add(worker)
    await async_db_session.commit()
    
    # Check voice consent - should default to False
    has_voice = await check_worker_voice_consent(async_db_session, worker_id)
    assert has_voice is False


@pytest.mark.asyncio
async def test_update_worker_coaching_consent_opt_in(async_db_session):
    """Test updating worker coaching consent to opt-in."""
    worker_id = uuid4()
    
    # Create user without coaching consent
    user = User(
        id=worker_id,
        phone_number="+8801712345684",
        user_type=UserType.WORKER,
        name="Update Worker",
        consent={"sms": True}
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Update to opt-in
    success = await update_worker_coaching_consent(
        async_db_session,
        worker_id,
        coaching_enabled=True
    )
    assert success is True
    
    # Verify consent was updated
    await async_db_session.refresh(user)
    assert user.consent['coaching_enabled'] is True
    assert 'updated_at' in user.consent


@pytest.mark.asyncio
async def test_update_worker_coaching_consent_opt_out(async_db_session):
    """Test updating worker coaching consent to opt-out."""
    worker_id = uuid4()
    
    # Create user with coaching enabled
    user = User(
        id=worker_id,
        phone_number="+8801712345685",
        user_type=UserType.WORKER,
        name="Opt Out Worker",
        consent={"coaching_enabled": True, "sms": True}
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Update to opt-out
    success = await update_worker_coaching_consent(
        async_db_session,
        worker_id,
        coaching_enabled=False
    )
    assert success is True
    
    # Verify consent was updated
    await async_db_session.refresh(user)
    assert user.consent['coaching_enabled'] is False


@pytest.mark.asyncio
async def test_update_worker_coaching_consent_worker_not_found(async_db_session):
    """Test updating consent for non-existent worker."""
    nonexistent_id = uuid4()
    
    success = await update_worker_coaching_consent(
        async_db_session,
        nonexistent_id,
        coaching_enabled=True
    )
    assert success is False


@pytest.mark.asyncio
async def test_worker_coaching_consent_creates_consent_if_none(async_db_session):
    """Test that updating consent creates consent object if it doesn't exist."""
    worker_id = uuid4()
    
    # Create user with None consent
    user = User(
        id=worker_id,
        phone_number="+8801712345686",
        user_type=UserType.WORKER,
        name="No Consent Worker",
        consent=None
    )
    async_db_session.add(user)
    await async_db_session.commit()
    
    # Update coaching consent
    success = await update_worker_coaching_consent(
        async_db_session,
        worker_id,
        coaching_enabled=True
    )
    assert success is True
    
    # Verify consent object was created
    await async_db_session.refresh(user)
    assert user.consent is not None
    assert user.consent['coaching_enabled'] is True
