"""
Unit tests for consent and frequency cap utilities.
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.lib.consent import (
    check_consent,
    check_frequency_cap,
    update_consent,
    can_send_notification,
    DEFAULT_CAPS,
)
from src.models.ai_messages import MessageChannel, MessageRole
from src.models.users import User
from src.models.workers import Worker


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_consent_customer_sms_granted():
    """Test consent check for customer with SMS consent granted."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user with SMS consent
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": True, "push": True, "whatsapp": False}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    # Check consent
    has_consent = await check_consent(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert has_consent is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_consent_customer_sms_denied():
    """Test consent check for customer with SMS consent denied."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user without SMS consent
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": False, "push": True, "whatsapp": False}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    has_consent = await check_consent(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert has_consent is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_consent_user_not_found():
    """Test consent check when user doesn't exist."""
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    has_consent = await check_consent(
        db=mock_db,
        user_id=uuid4(),
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert has_consent is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_consent_worker():
    """Test consent check for worker."""
    mock_db = AsyncMock()
    worker_id = uuid4()
    
    # Mock worker
    mock_worker = Worker(id=worker_id)
    
    # Mock user with consent
    mock_user = User(
        id=worker_id,
        phone="+8801712345678",
        consent={"sms": True, "push": True}
    )
    
    # Setup mock to return worker first, then user
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_worker)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
    ]
    
    has_consent = await check_consent(
        db=mock_db,
        worker_id=worker_id,
        channel=MessageChannel.SMS,
        role=MessageRole.WORKER
    )
    
    assert has_consent is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_frequency_cap_under_daily_limit():
    """Test frequency cap when under daily limit."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock count query - 2 messages sent today (under cap of 3)
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=2)),  # Daily count
        MagicMock(scalar=MagicMock(return_value=5)),  # Weekly count
    ]
    
    allowed, reason = await check_frequency_cap(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is True
    assert reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_frequency_cap_daily_limit_exceeded():
    """Test frequency cap when daily limit exceeded."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock count query - 3 messages sent today (at cap)
    mock_db.execute.return_value = MagicMock(scalar=MagicMock(return_value=3))
    
    allowed, reason = await check_frequency_cap(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is False
    assert "Daily cap exceeded" in reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_frequency_cap_weekly_limit_exceeded():
    """Test frequency cap when weekly limit exceeded."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock count queries - under daily but at weekly cap
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=2)),   # Daily: 2 (under)
        MagicMock(scalar=MagicMock(return_value=10)),  # Weekly: 10 (at cap)
    ]
    
    allowed, reason = await check_frequency_cap(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is False
    assert "Weekly cap exceeded" in reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_frequency_cap_custom_caps():
    """Test frequency cap with custom limits."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Custom caps: only 1 SMS per day
    custom_caps = {"sms_per_day": 1, "sms_per_week": 5}
    
    # Mock: already sent 1 message today
    mock_db.execute.return_value = MagicMock(scalar=MagicMock(return_value=1))
    
    allowed, reason = await check_frequency_cap(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER,
        caps=custom_caps
    )
    
    assert allowed is False
    assert "Daily cap exceeded: 1/1" in reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_consent_success():
    """Test updating user consent."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": False, "push": True}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    
    # Update consent to opt-in to SMS
    success = await update_consent(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        consented=True
    )
    
    assert success is True
    assert mock_user.consent["sms"] is True
    assert "updated_at" in mock_user.consent
    assert mock_db.commit.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_consent_user_not_found():
    """Test updating consent for non-existent user."""
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    success = await update_consent(
        db=mock_db,
        user_id=uuid4(),
        channel=MessageChannel.SMS,
        consented=True
    )
    
    assert success is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_can_send_notification_allowed():
    """Test combined check when all conditions pass."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user with consent
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": True}
    )
    
    # Mock consent check (user query)
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
        # Frequency cap queries
        MagicMock(scalar=MagicMock(return_value=1)),  # Daily: 1
        MagicMock(scalar=MagicMock(return_value=3)),  # Weekly: 3
    ]
    
    allowed, reason = await can_send_notification(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is True
    assert reason is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_can_send_notification_no_consent():
    """Test combined check when consent is denied."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user without consent
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": False}
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_db.execute.return_value = mock_result
    
    allowed, reason = await can_send_notification(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is False
    assert "not consented" in reason


@pytest.mark.unit
@pytest.mark.asyncio
async def test_can_send_notification_frequency_cap_exceeded():
    """Test combined check when frequency cap exceeded."""
    mock_db = AsyncMock()
    user_id = uuid4()
    
    # Mock user with consent
    mock_user = User(
        id=user_id,
        phone="+8801712345678",
        consent={"sms": True}
    )
    
    # Mock consent check + frequency cap queries
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=mock_user)),
        MagicMock(scalar=MagicMock(return_value=3)),  # Daily: at cap
    ]
    
    allowed, reason = await can_send_notification(
        db=mock_db,
        user_id=user_id,
        channel=MessageChannel.SMS,
        role=MessageRole.CUSTOMER
    )
    
    assert allowed is False
    assert "Daily cap exceeded" in reason


@pytest.mark.unit
def test_default_caps_exist():
    """Test that default frequency caps are defined."""
    assert "sms_per_day" in DEFAULT_CAPS
    assert "sms_per_week" in DEFAULT_CAPS
    assert "push_per_day" in DEFAULT_CAPS
    assert "push_per_week" in DEFAULT_CAPS
    assert DEFAULT_CAPS["sms_per_day"] == 3
    assert DEFAULT_CAPS["sms_per_week"] == 10
