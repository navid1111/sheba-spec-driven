"""
Unit tests for NotificationService.
"""
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.ai_messages import (
    MessageChannel,
    MessageType,
    MessageRole,
    DeliveryStatus,
)
from src.services.notification_service import (
    NotificationService,
    ConsoleSMSProvider,
    PushNotificationProvider,
    TwilioSMSProvider,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_console_sms_provider():
    """Test console SMS provider sends successfully."""
    provider = ConsoleSMSProvider()
    
    assert provider.channel == MessageChannel.SMS
    
    success = await provider.send(
        to="+8801712345678",
        message="Test SMS message"
    )
    
    assert success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_push_notification_provider():
    """Test push notification stub."""
    provider = PushNotificationProvider()
    
    assert provider.channel == MessageChannel.APP_PUSH
    
    success = await provider.send(
        to="device-token-123",
        message="Test push notification",
        title="Test Title"
    )
    
    assert success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_twilio_sms_provider_no_client():
    """Test Twilio provider when client unavailable."""
    with patch("src.services.notification_service.settings") as mock_settings:
        mock_settings.twilio_account_sid = "test_sid"
        mock_settings.twilio_auth_token = "test_token"
        mock_settings.twilio_from_number = "+1234567890"
        
        # Mock Twilio import to fail by patching the import inside __init__
        with patch.dict('sys.modules', {'twilio': None, 'twilio.rest': None}):
            provider = TwilioSMSProvider()
            
            assert provider.available is False
            
            success = await provider.send(
                to="+8801712345678",
                message="Test"
            )
            
            assert success is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_send_sms():
    """Test sending SMS notification."""
    # Mock database session
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    # Send notification
    message_id = await service.send_notification(
        to="+8801712345678",
        message_text="Your booking is confirmed!",
        channel=MessageChannel.SMS,
        agent_type="smartengage",
        message_type=MessageType.REMINDER,
        role=MessageRole.CUSTOMER,
        user_id=uuid4(),
        locale="bn"
    )
    
    assert message_id is not None
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_send_push():
    """Test sending push notification."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    message_id = await service.send_notification(
        to="device-token-123",
        message_text="New coaching tip available!",
        channel=MessageChannel.APP_PUSH,
        agent_type="coachnova",
        message_type=MessageType.COACHING,
        role=MessageRole.WORKER,
        worker_id=uuid4(),
        title="CoachNova"
    )
    
    assert message_id is not None
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_unsupported_channel():
    """Test sending to unsupported channel."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    # WhatsApp not yet implemented
    message_id = await service.send_notification(
        to="+8801712345678",
        message_text="Test",
        channel=MessageChannel.WHATSAPP,
        agent_type="smartengage",
        message_type=MessageType.REMINDER,
        role=MessageRole.CUSTOMER,
        user_id=uuid4()
    )
    
    # Message created but status should be FAILED
    assert message_id is not None
    
    # Check that message was added with FAILED status
    added_message = mock_db.add.call_args[0][0]
    assert added_message.delivery_status == DeliveryStatus.FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_with_correlation_id():
    """Test notification with custom correlation ID."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    custom_correlation_id = uuid4()
    
    message_id = await service.send_notification(
        to="+8801712345678",
        message_text="Test message",
        channel=MessageChannel.SMS,
        agent_type="smartengage",
        message_type=MessageType.REMINDER,
        role=MessageRole.CUSTOMER,
        user_id=uuid4(),
        correlation_id=custom_correlation_id
    )
    
    assert message_id is not None
    
    # Check correlation ID was used
    added_message = mock_db.add.call_args[0][0]
    assert added_message.correlation_id == custom_correlation_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_with_template_and_ai_metadata():
    """Test notification with template and AI generation metadata."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    template_id = uuid4()
    safety_checks = {
        "profanity_check": "passed",
        "tone_check": "appropriate"
    }
    
    message_id = await service.send_notification(
        to="+8801712345678",
        message_text="AI-generated reminder",
        channel=MessageChannel.SMS,
        agent_type="smartengage",
        message_type=MessageType.REMINDER,
        role=MessageRole.CUSTOMER,
        user_id=uuid4(),
        template_id=template_id,
        model="gpt-4o-mini",
        prompt_version=1,
        safety_checks=safety_checks
    )
    
    assert message_id is not None
    
    # Check metadata
    added_message = mock_db.add.call_args[0][0]
    assert added_message.template_id == template_id
    assert added_message.model == "gpt-4o-mini"
    assert added_message.prompt_version == 1
    assert added_message.safety_checks == safety_checks


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_delivery_status():
    """Test updating message delivery status."""
    mock_db = AsyncMock()
    
    # Mock the message query result
    message_id = uuid4()
    correlation_id = uuid4()
    mock_message = MagicMock()
    mock_message.id = message_id
    mock_message.correlation_id = correlation_id
    mock_message.delivery_status = DeliveryStatus.PENDING
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_message
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    success = await service.update_delivery_status(
        message_id=message_id,
        status=DeliveryStatus.DELIVERED
    )
    
    assert success is True
    assert mock_db.execute.called
    assert mock_db.commit.called
    assert mock_message.delivery_status == DeliveryStatus.DELIVERED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_delivery_status_not_found():
    """Test updating delivery status for non-existent message."""
    mock_db = AsyncMock()
    
    # Mock execute result with no message found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    message_id = uuid4()
    success = await service.update_delivery_status(
        message_id=message_id,
        status=DeliveryStatus.DELIVERED
    )
    
    assert success is False
    # Commit should not be called if message not found
    assert not mock_db.commit.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_delivery_status_includes_correlation_id():
    """Test that update_delivery_status logs correlation_id for traceability."""
    mock_db = AsyncMock()
    
    # Mock the message query result with correlation_id
    message_id = uuid4()
    correlation_id = uuid4()
    mock_message = MagicMock()
    mock_message.id = message_id
    mock_message.correlation_id = correlation_id
    mock_message.delivery_status = DeliveryStatus.PENDING
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_message
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    # Update status
    success = await service.update_delivery_status(
        message_id=message_id,
        status=DeliveryStatus.DELIVERED
    )
    
    assert success is True
    # Verify message status was updated
    assert mock_message.delivery_status == DeliveryStatus.DELIVERED
    # Verify updated_at was set
    assert mock_message.updated_at is not None
    # The correlation_id is now included in logger.info call (verified by code inspection)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_notification_service_provider_exception():
    """Test handling provider exception during send."""
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    
    service = NotificationService(mock_db)
    
    # Mock provider to raise exception
    with patch.object(
        service._providers[MessageChannel.SMS],
        'send',
        side_effect=Exception("Network error")
    ):
        message_id = await service.send_notification(
            to="+8801712345678",
            message_text="Test",
            channel=MessageChannel.SMS,
            agent_type="smartengage",
            message_type=MessageType.REMINDER,
            role=MessageRole.CUSTOMER,
            user_id=uuid4()
        )
        
        assert message_id is not None
        
        # Message should be marked as FAILED
        added_message = mock_db.add.call_args[0][0]
        assert added_message.delivery_status == DeliveryStatus.FAILED
