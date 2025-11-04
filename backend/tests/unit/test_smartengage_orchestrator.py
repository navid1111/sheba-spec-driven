"""
Unit tests for SmartEngage Orchestrator.

Tests cover:
- Message generation with OpenAI (mocked)
- Safety filter integration
- Deep link generation
- Email notification
- AIMessage record creation
- Error handling and fallbacks
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from src.ai.smartengage import SmartEngageOrchestrator
from src.models.users import User, UserType
from src.models.customers import Customer
from src.models.bookings import Booking, BookingStatus
from src.models.services import Service, ServiceCategory
from src.models.ai_messages import AIMessage, DeliveryStatus, MessageChannel


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = MagicMock()
    
    # Mock the chat completion response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="আপনার হোম ক্লিনিং সার্ভিসের সময় হয়ে গেছে! এখনই বুক করে ঘর ঝকঝকে করুন।"
            )
        )
    ]
    client.get_client.return_value.chat.completions.create.return_value = mock_response
    client.is_available.return_value = True
    
    return client


@pytest.fixture
def mock_safety_filter():
    """Mock safety filter."""
    filter_instance = MagicMock()
    
    # Default: pass all checks
    async def mock_check(text, **kwargs):
        return {
            "safe": True,
            "checks": {
                "length": {"status": "passed", "length": len(text)},
                "banned_phrases": {"status": "passed", "matches": None},
                "tone": {"status": "passed", "category": "professional", "confidence": 0.8},
            },
        }
    
    filter_instance.check_message = AsyncMock(side_effect=mock_check)
    filter_instance.get_fallback_message.return_value = "আপনার সার্ভিস বুকিংয়ের রিমাইন্ডার।"
    
    return filter_instance


@pytest.fixture
def mock_deeplink_generator():
    """Mock deep link generator."""
    generator = MagicMock()
    generator.generate_booking_link.return_value = (
        "https://app.sheba.xyz/booking?token=test-jwt-token&utm_source=smartengage"
    )
    return generator


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    service = MagicMock()
    
    # Mock email provider
    email_provider = MagicMock()
    email_provider.send = AsyncMock(return_value=True)
    
    service.get_provider.return_value = email_provider
    
    return service


@pytest.fixture
def mock_segmentation_service():
    """Mock segmentation service."""
    service = MagicMock()
    return service


@pytest.fixture
def sample_customer_data():
    """Sample customer data for tests."""
    customer_id = uuid4()
    service_id = uuid4()
    
    user = User(
        id=customer_id,
        email="test@example.com",
        name="Test Customer",
        type=UserType.CUSTOMER,
        language_preference="bn",
        is_active=True,
        consent={"marketing": True, "notifications": True},
    )
    
    customer = Customer(
        id=customer_id,
        typical_services=["CLEANING"],
        last_booking_at=datetime.now(timezone.utc) - timedelta(days=21),
    )
    
    service = Service(
        id=service_id,
        name="Home Cleaning",
        name_bn="হোম ক্লিনিং",
        category=ServiceCategory.CLEANING,
        description="Regular cleaning",
        base_price=500.00,
        duration_minutes=120,
        active=True,
    )
    
    booking = Booking(
        id=uuid4(),
        customer_id=customer_id,
        service_id=service_id,
        status=BookingStatus.COMPLETED,
        scheduled_at=datetime.now(timezone.utc) - timedelta(days=21),
        finished_at=datetime.now(timezone.utc) - timedelta(days=21),
        total_price=500.00,
    )
    
    return {
        "user": user,
        "customer": customer,
        "service": service,
        "booking": booking,
    }


@pytest.fixture
def orchestrator(
    mock_db,
    mock_openai_client,
    mock_safety_filter,
    mock_deeplink_generator,
    mock_notification_service,
    mock_segmentation_service,
):
    """Create SmartEngageOrchestrator with mocked dependencies."""
    return SmartEngageOrchestrator(
        db_session=mock_db,
        openai_client=mock_openai_client,
        safety_filter=mock_safety_filter,
        deeplink_generator=mock_deeplink_generator,
        notification_service=mock_notification_service,
        segmentation_service=mock_segmentation_service,
    )


# ============================================================================
# Test: Message Generation
# ============================================================================


@pytest.mark.asyncio
async def test_generate_message_with_openai_success(
    orchestrator,
    sample_customer_data,
    mock_openai_client,
):
    """Test successful message generation with OpenAI."""
    customer = sample_customer_data["customer"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    message = await orchestrator._generate_message_with_openai(
        customer, service, booking, promo_code="CLEAN20"
    )
    
    # Verify message was generated
    assert message == "আপনার হোম ক্লিনিং সার্ভিসের সময় হয়ে গেছে! এখনই বুক করে ঘর ঝকঝকে করুন।"
    
    # Verify OpenAI was called
    mock_openai_client.get_client.assert_called_once()


@pytest.mark.asyncio
async def test_generate_message_openai_not_available(
    orchestrator,
    sample_customer_data,
    mock_openai_client,
):
    """Test error when OpenAI is not configured."""
    mock_openai_client.is_available.return_value = False
    
    customer = sample_customer_data["customer"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    with pytest.raises(ValueError, match="OpenAI client not configured"):
        await orchestrator._generate_message_with_openai(customer, service, booking)


@pytest.mark.asyncio
async def test_build_reminder_prompt_with_promo(orchestrator):
    """Test prompt building with promo code."""
    context = {
        "customer_name": "Test Customer",
        "service_name": "Home Cleaning",
        "service_name_bn": "হোম ক্লিনিং",
        "days_since": 21,
        "promo_code": "CLEAN20",
        "has_promo": True,
    }
    
    prompt = orchestrator._build_reminder_prompt(context)
    
    assert "Test Customer" in prompt
    assert "হোম ক্লিনিং" in prompt
    assert "21 দিন আগে" in prompt
    assert "CLEAN20" in prompt


@pytest.mark.asyncio
async def test_build_reminder_prompt_without_promo(orchestrator):
    """Test prompt building without promo code."""
    context = {
        "customer_name": "Test Customer",
        "service_name": "Home Cleaning",
        "service_name_bn": "হোম ক্লিনিং",
        "days_since": 21,
        "promo_code": None,
        "has_promo": False,
    }
    
    prompt = orchestrator._build_reminder_prompt(context)
    
    assert "Test Customer" in prompt
    assert "হোম ক্লিনিং" in prompt
    assert "প্রোমো কোড" not in prompt  # Should not mention promo if not present


# ============================================================================
# Test: Safety Filter Integration
# ============================================================================


@pytest.mark.asyncio
async def test_apply_safety_filter_pass(
    orchestrator,
    mock_safety_filter,
):
    """Test safety filter passing clean message."""
    correlation_id = uuid4()
    
    result = await orchestrator._apply_safety_filter(
        "আপনার সার্ভিস বুকিংয়ের সময় হয়ে গেছে।",
        correlation_id,
    )
    
    assert result["safe"] is True
    assert "checks" in result
    mock_safety_filter.check_message.assert_called_once()


@pytest.mark.asyncio
async def test_apply_safety_filter_reject(
    orchestrator,
    mock_safety_filter,
):
    """Test safety filter rejecting inappropriate message."""
    correlation_id = uuid4()
    
    # Mock rejection
    async def mock_reject(text, **kwargs):
        return {
            "safe": False,
            "checks": {
                "banned_phrases": {"status": "failed", "matches": ["banned_word"]},
            },
            "reason": "Contains banned phrases",
        }
    
    mock_safety_filter.check_message = AsyncMock(side_effect=mock_reject)
    
    result = await orchestrator._apply_safety_filter(
        "Message with banned_word",
        correlation_id,
    )
    
    assert result["safe"] is False
    assert result["reason"] == "Contains banned phrases"


# ============================================================================
# Test: Full Orchestration Flow
# ============================================================================


@pytest.mark.asyncio
async def test_generate_and_send_reminder_success(
    orchestrator,
    sample_customer_data,
    mock_db,
    mock_deeplink_generator,
    mock_notification_service,
):
    """Test successful end-to-end reminder generation and sending."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    # Mock database queries
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
        Service: service,
    }.get(model)
    
    # Mock segmentation service
    orchestrator.segmentation_service.get_last_booking.return_value = booking
    
    # Generate and send
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
        promo_code="CLEAN20",
    )
    
    # Verify success
    assert result["success"] is True
    assert "message_id" in result
    assert "correlation_id" in result
    
    # Verify AIMessage was created
    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    
    # Verify deep link was generated
    mock_deeplink_generator.generate_booking_link.assert_called_once_with(
        customer_id=customer.id,
        service_id=service.id,
        promo_code="CLEAN20",
        ttl_hours=48,
        utm_campaign="smartengage_reminder",
        metadata=ANY,
    )
    
    # Verify notification was sent
    email_provider = mock_notification_service.get_provider.return_value
    email_provider.send.assert_called_once()
    call_args = email_provider.send.call_args[1]
    assert call_args["to"] == user.email
    assert "হোম ক্লিনিং" in call_args["subject"]


@pytest.mark.asyncio
async def test_generate_and_send_reminder_customer_not_found(
    orchestrator,
    mock_db,
):
    """Test failure when customer doesn't exist."""
    mock_db.get.return_value = None
    
    result = await orchestrator.generate_and_send_reminder(
        customer_id=uuid4(),
    )
    
    assert result["success"] is False
    assert result["reason"] == "Customer not found"


@pytest.mark.asyncio
async def test_generate_and_send_reminder_no_consent(
    orchestrator,
    sample_customer_data,
    mock_db,
):
    """Test skipping customer without marketing consent."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    user.consent = {"marketing": False}  # No consent
    
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
    }.get(model)
    
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
    )
    
    assert result["success"] is False
    assert result["reason"] == "No marketing consent"


@pytest.mark.asyncio
async def test_generate_and_send_reminder_no_booking_history(
    orchestrator,
    sample_customer_data,
    mock_db,
):
    """Test failure when customer has no booking history."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
    }.get(model)
    
    orchestrator.segmentation_service.get_last_booking.return_value = None
    
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
    )
    
    assert result["success"] is False
    assert result["reason"] == "No booking history"


@pytest.mark.asyncio
async def test_generate_and_send_reminder_openai_failure_uses_fallback(
    orchestrator,
    sample_customer_data,
    mock_db,
    mock_openai_client,
    mock_safety_filter,
    mock_notification_service,
):
    """Test fallback message when OpenAI fails."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
        Service: service,
    }.get(model)
    
    orchestrator.segmentation_service.get_last_booking.return_value = booking
    
    # Mock OpenAI failure
    mock_openai_client.get_client.return_value.chat.completions.create.side_effect = Exception(
        "OpenAI API error"
    )
    
    # Should use fallback
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
    )
    
    # Should still succeed with fallback message
    assert result["success"] is True
    
    # Verify fallback was used
    mock_safety_filter.get_fallback_message.assert_called()
    
    # Verify notification was sent (with fallback content)
    email_provider = mock_notification_service.get_provider.return_value
    email_provider.send.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_send_reminder_safety_rejection_uses_fallback(
    orchestrator,
    sample_customer_data,
    mock_db,
    mock_safety_filter,
    mock_notification_service,
):
    """Test fallback when safety filter rejects message."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
        Service: service,
    }.get(model)
    
    orchestrator.segmentation_service.get_last_booking.return_value = booking
    
    # Mock safety rejection on first call, then pass on second (fallback)
    call_count = 0
    
    async def mock_check_with_reject(text, **kwargs):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # Reject original message
            return {
                "safe": False,
                "checks": {"tone": {"status": "failed"}},
                "reason": "Inappropriate tone",
            }
        else:
            # Pass fallback
            return {
                "safe": True,
                "checks": {"tone": {"status": "passed"}},
            }
    
    mock_safety_filter.check_message = AsyncMock(side_effect=mock_check_with_reject)
    
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
    )
    
    assert result["success"] is True
    
    # Should have checked twice (original + fallback)
    assert mock_safety_filter.check_message.call_count == 2
    mock_safety_filter.get_fallback_message.assert_called_once()


@pytest.mark.asyncio
async def test_generate_and_send_reminder_notification_failure(
    orchestrator,
    sample_customer_data,
    mock_db,
    mock_notification_service,
):
    """Test handling when notification sending fails."""
    customer = sample_customer_data["customer"]
    user = sample_customer_data["user"]
    service = sample_customer_data["service"]
    booking = sample_customer_data["booking"]
    
    mock_db.get.side_effect = lambda model, id: {
        Customer: customer,
        User: user,
        Service: service,
    }.get(model)
    
    orchestrator.segmentation_service.get_last_booking.return_value = booking
    
    # Mock notification failure from email provider
    email_provider = mock_notification_service.get_provider.return_value
    email_provider.send.side_effect = Exception("SMTP connection failed")
    
    result = await orchestrator.generate_and_send_reminder(
        customer_id=customer.id,
    )
    
    assert result["success"] is False
    assert "Notification failed" in result["reason"]
    assert "message_id" in result  # Message was created before sending failed


# ============================================================================
# Test: Email HTML Building
# ============================================================================


def test_build_email_html_with_promo(orchestrator):
    """Test email HTML generation with promo code."""
    html = orchestrator._build_email_html(
        message_text="আপনার সার্ভিস বুকিংয়ের সময় হয়ে গেছে!",
        deep_link="https://app.sheba.xyz/booking?token=test",
        customer_name="Test Customer",
        service_name="হোম ক্লিনিং",
        promo_code="CLEAN20",
    )
    
    assert "Test Customer" in html
    assert "আপনার সার্ভিস বুকিংয়ের সময় হয়ে গেছে!" in html
    assert "CLEAN20" in html
    assert "https://app.sheba.xyz/booking?token=test" in html
    assert "এখনই বুক করুন" in html
    assert "<!DOCTYPE html>" in html


def test_build_email_html_without_promo(orchestrator):
    """Test email HTML generation without promo code."""
    html = orchestrator._build_email_html(
        message_text="আপনার সার্ভিস বুকিংয়ের সময় হয়ে গেছে!",
        deep_link="https://app.sheba.xyz/booking?token=test",
        customer_name="Test Customer",
        service_name="হোম ক্লিনিং",
        promo_code=None,
    )
    
    assert "Test Customer" in html
    assert "CLEAN20" not in html  # No promo section
    assert "প্রোমো কোড:" not in html


# ============================================================================
# Test: Bulk Reminders
# ============================================================================


@pytest.mark.asyncio
async def test_generate_and_send_bulk_reminders(
    orchestrator,
    sample_customer_data,
):
    """Test bulk reminder sending to multiple customers."""
    # Mock 3 eligible customers
    customer1 = sample_customer_data["customer"]
    customer2 = Customer(
        id=uuid4(),
        typical_services=["CLEANING"],
        last_booking_at=datetime.now(timezone.utc) - timedelta(days=21),
    )
    customer3 = Customer(
        id=uuid4(),
        typical_services=["CLEANING"],
        last_booking_at=datetime.now(timezone.utc) - timedelta(days=21),
    )
    
    orchestrator.segmentation_service.find_eligible_for_reminders.return_value = [
        customer1,
        customer2,
        customer3,
    ]
    
    # Mock individual reminder results
    orchestrator.generate_and_send_reminder = AsyncMock(
        return_value={"success": True, "message_id": uuid4(), "correlation_id": uuid4()}
    )
    
    result = await orchestrator.generate_and_send_bulk_reminders(
        booking_cadence_days=21,
        batch_size=2,  # Test batching with 2 per batch
    )
    
    assert result["total_eligible"] == 3
    assert result["sent"] == 3
    assert result["failed"] == 0
    assert result["skipped"] == 0
    
    # Verify called for each customer
    assert orchestrator.generate_and_send_reminder.call_count == 3


@pytest.mark.asyncio
async def test_generate_and_send_bulk_reminders_with_failures(
    orchestrator,
    sample_customer_data,
):
    """Test bulk sending with some failures."""
    customer1 = sample_customer_data["customer"]
    customer2 = Customer(id=uuid4(), typical_services=["CLEANING"])
    
    orchestrator.segmentation_service.find_eligible_for_reminders.return_value = [
        customer1,
        customer2,
    ]
    
    # Mock mixed results (one success, one failure)
    orchestrator.generate_and_send_reminder = AsyncMock(
        side_effect=[
            {"success": True, "message_id": uuid4(), "correlation_id": uuid4()},
            {"success": False, "reason": "No booking history"},
        ]
    )
    
    result = await orchestrator.generate_and_send_bulk_reminders()
    
    assert result["total_eligible"] == 2
    assert result["sent"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 1


# ============================================================================
# Test: Factory Function
# ============================================================================


def test_get_smartengage_orchestrator():
    """Test factory function creates orchestrator."""
    from src.ai.smartengage import get_smartengage_orchestrator
    
    mock_db = MagicMock()
    orchestrator = get_smartengage_orchestrator(mock_db)
    
    assert isinstance(orchestrator, SmartEngageOrchestrator)
    assert orchestrator.db == mock_db
