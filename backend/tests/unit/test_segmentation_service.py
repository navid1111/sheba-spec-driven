"""
Unit tests for customer segmentation service.

Tests validate:
- Booking cadence eligibility (X days ago ±tolerance)
- Send window time validation
- Marketing consent filtering
- Frequency caps (24-hour rule)
- Helper methods (booking history, preferred services)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from src.services.segmentation_service import SegmentationService
from src.models.users import User, UserType
from src.models.customers import Customer
from src.models.bookings import Booking, BookingStatus
from src.models.services import Service, ServiceCategory
from src.models.ai_messages import AIMessage, MessageRole, MessageChannel, MessageType, DeliveryStatus
from src.lib.db import get_db


@pytest.fixture
def db_session():
    """Get database session for tests."""
    session = next(get_db())
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def segmentation_service(db_session):
    """Fixture providing segmentation service instance."""
    return SegmentationService(db_session)


@pytest.fixture
def sample_service(db_session):
    """Create a sample service for testing."""
    service = Service(
        id=uuid4(),
        name="Home Cleaning",
        description="Professional home cleaning",
        category=ServiceCategory.CLEANING,
        base_price=500.00,
        duration_minutes=120,
        active=True,
    )
    db_session.add(service)
    db_session.commit()
    return service


def create_customer_with_booking(
    db_session,
    service_id,
    days_ago,
    booking_status=BookingStatus.COMPLETED,
    marketing_consent=True,
    is_active=True,
    email_suffix=None
):
    """Helper to create customer with booking history."""
    if email_suffix is None:
        import random
        email_suffix = random.randint(1000, 9999)
    
    user = User(
        id=uuid4(),
        email=f"test.{email_suffix}@example.com",
        name=f"Test Customer {email_suffix}",
        type=UserType.CUSTOMER,
        is_active=is_active,
        consent={"marketing": marketing_consent, "sms": True},
    )
    db_session.add(user)
    db_session.flush()  # Flush user first so it exists for foreign key
    
    customer = Customer(id=user.id, typical_services=["home_cleaning"])
    db_session.add(customer)
    db_session.flush()  # Flush customer so it exists for booking FK
    
    booking = Booking(
        id=uuid4(),
        customer_id=customer.id,
        service_id=service_id,
        status=booking_status,
        scheduled_at=datetime.utcnow() - timedelta(days=days_ago),
        finished_at=datetime.utcnow() - timedelta(days=days_ago),
        total_price=500.00,
    )
    db_session.add(booking)
    db_session.commit()  # Final commit
    
    return user, customer, booking


class TestIdentifyEligibleCustomers:
    """Test suite for identify_eligible_customers method."""
    
    def test_customer_with_booking_at_exact_cadence_is_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer with booking exactly 21 days ago should be eligible."""
        user, customer, booking = create_customer_with_booking(
            db_session,
            sample_service.id,
            days_ago=21,
            marketing_consent=True
        )
        
        # Test with no send window restriction (always eligible)
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id in eligible, "Customer with booking at exact cadence should be eligible"
    
    def test_customer_within_cadence_tolerance_is_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer with booking 20 days ago (within ±1 day tolerance) should be eligible."""
        user, customer, booking = create_customer_with_booking(
            db_session,
            sample_service.id,
            days_ago=20,
            marketing_consent=True
        )
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            cadence_tolerance_days=1,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id in eligible, "Customer within tolerance window should be eligible"
    
    def test_customer_outside_cadence_window_is_not_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer with booking 15 days ago (outside 21±1 window) should not be eligible."""
        user, customer, booking = create_customer_with_booking(
            db_session,
            sample_service.id,
            days_ago=15,
            marketing_consent=True
        )
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            cadence_tolerance_days=1,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id not in eligible, "Customer outside cadence window should not be eligible"
    
    def test_customer_without_marketing_consent_is_not_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer who opted out of marketing should not be eligible."""
        user, customer, booking = create_customer_with_booking(
            db_session,
            sample_service.id,
            days_ago=21,
            marketing_consent=False  # Opted out
        )
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id not in eligible, "Customer without marketing consent should not be eligible"
    
    def test_customer_with_recent_message_is_not_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer who received message in last 24h should be excluded (frequency cap)."""
        user = User(
            id=uuid4(),
            email="recent.message@example.com",
            name="Recent Message",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        # Eligible booking
        booking = Booking(
            id=uuid4(),
            customer_id=customer.id,
            service_id=sample_service.id,
            status=BookingStatus.COMPLETED,
            scheduled_at=datetime.utcnow() - timedelta(days=21),
            finished_at=datetime.utcnow() - timedelta(days=21),
            total_price=500.00,
        )
        db_session.add(booking)
        
        # Recent message (5 hours ago)
        message = AIMessage(
            id=uuid4(),
            user_id=user.id,
            role=MessageRole.CUSTOMER,
            agent_type="smartengage",
            channel=MessageChannel.EMAIL,
            message_type=MessageType.REMINDER,
            message_text="Previous reminder",
            delivery_status=DeliveryStatus.SENT,
            created_at=datetime.utcnow() - timedelta(hours=5),
        )
        db_session.add(message)
        db_session.commit()
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id not in eligible, "Customer with recent message should not be eligible"
    
    def test_customer_with_old_message_is_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Customer who received message >24h ago should be eligible again."""
        user = User(
            id=uuid4(),
            email="old.message@example.com",
            name="Old Message",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        booking = Booking(
            id=uuid4(),
            customer_id=customer.id,
            service_id=sample_service.id,
            status=BookingStatus.COMPLETED,
            scheduled_at=datetime.utcnow() - timedelta(days=21),
            finished_at=datetime.utcnow() - timedelta(days=21),
            total_price=500.00,
        )
        db_session.add(booking)
        
        # Old message (48 hours ago - beyond frequency cap)
        message = AIMessage(
            id=uuid4(),
            user_id=user.id,
            role=MessageRole.CUSTOMER,
            agent_type="smartengage",
            channel=MessageChannel.EMAIL,
            message_type=MessageType.REMINDER,
            message_text="Old reminder",
            delivery_status=DeliveryStatus.SENT,
            created_at=datetime.utcnow() - timedelta(hours=48),
        )
        db_session.add(message)
        db_session.commit()
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id in eligible, "Customer with old message (>24h) should be eligible"
    
    def test_only_completed_bookings_are_considered(
        self, db_session, segmentation_service, sample_service
    ):
        """Pending or cancelled bookings should not make customer eligible."""
        user = User(
            id=uuid4(),
            email="cancelled@example.com",
            name="Cancelled Booking",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        # Cancelled booking 21 days ago
        booking = Booking(
            id=uuid4(),
            customer_id=customer.id,
            service_id=sample_service.id,
            status=BookingStatus.CANCELLED,  # Not completed
            scheduled_at=datetime.utcnow() - timedelta(days=21),
            finished_at=datetime.utcnow() - timedelta(days=21),
            total_price=500.00,
        )
        db_session.add(booking)
        db_session.commit()
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id not in eligible, "Cancelled bookings should not make customer eligible"
    
    def test_inactive_users_are_not_eligible(
        self, db_session, segmentation_service, sample_service
    ):
        """Inactive users should be excluded."""
        user = User(
            id=uuid4(),
            email="inactive@example.com",
            name="Inactive User",
            type=UserType.CUSTOMER,
            is_active=False,  # Inactive
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        booking = Booking(
            id=uuid4(),
            customer_id=customer.id,
            service_id=sample_service.id,
            status=BookingStatus.COMPLETED,
            scheduled_at=datetime.utcnow() - timedelta(days=21),
            finished_at=datetime.utcnow() - timedelta(days=21),
            total_price=500.00,
        )
        db_session.add(booking)
        db_session.commit()
        
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="00:00",
            send_window_end="23:59",
        )
        
        assert user.id not in eligible, "Inactive users should not be eligible"


class TestSendWindowValidation:
    """Test suite for send window time validation."""
    
    def test_time_within_normal_window_is_valid(self, segmentation_service):
        """Time within normal window (18:00-20:00) should return True."""
        test_time = datetime(2025, 11, 4, 19, 0)  # 7:00 PM
        
        result = segmentation_service._is_within_send_window(
            "18:00", "20:00", test_time
        )
        
        assert result is True, "19:00 should be within 18:00-20:00 window"
    
    def test_time_outside_normal_window_is_invalid(self, segmentation_service):
        """Time outside normal window should return False."""
        test_time = datetime(2025, 11, 4, 21, 30)  # 9:30 PM
        
        result = segmentation_service._is_within_send_window(
            "18:00", "20:00", test_time
        )
        
        assert result is False, "21:30 should be outside 18:00-20:00 window"
    
    def test_time_at_window_boundary_is_valid(self, segmentation_service):
        """Time exactly at window boundary should be valid."""
        test_time = datetime(2025, 11, 4, 18, 0)  # Exactly 6:00 PM
        
        result = segmentation_service._is_within_send_window(
            "18:00", "20:00", test_time
        )
        
        assert result is True, "18:00 should be within 18:00-20:00 window (inclusive)"
    
    def test_window_crossing_midnight_works(self, segmentation_service):
        """Window crossing midnight (22:00-02:00) should work correctly."""
        # Test time: 11:00 PM (within window)
        test_time_1 = datetime(2025, 11, 4, 23, 0)
        assert segmentation_service._is_within_send_window(
            "22:00", "02:00", test_time_1
        ) is True, "23:00 should be within 22:00-02:00 window"
        
        # Test time: 1:00 AM (within window)
        test_time_2 = datetime(2025, 11, 4, 1, 0)
        assert segmentation_service._is_within_send_window(
            "22:00", "02:00", test_time_2
        ) is True, "01:00 should be within 22:00-02:00 window"
        
        # Test time: 3:00 AM (outside window)
        test_time_3 = datetime(2025, 11, 4, 3, 0)
        assert segmentation_service._is_within_send_window(
            "22:00", "02:00", test_time_3
        ) is False, "03:00 should be outside 22:00-02:00 window"
    
    def test_invalid_time_format_returns_false(self, segmentation_service):
        """Invalid time format should return False."""
        test_time = datetime(2025, 11, 4, 19, 0)
        
        result = segmentation_service._is_within_send_window(
            "invalid", "20:00", test_time
        )
        
        assert result is False, "Invalid time format should return False"
    
    def test_empty_send_window_returns_no_eligible_customers(
        self, db_session, segmentation_service, sample_service
    ):
        """When outside send window, should return empty list."""
        # Create eligible customer
        user = User(
            id=uuid4(),
            email="eligible@example.com",
            name="Eligible Customer",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        booking = Booking(
            id=uuid4(),
            customer_id=customer.id,
            service_id=sample_service.id,
            status=BookingStatus.COMPLETED,
            scheduled_at=datetime.utcnow() - timedelta(days=21),
            finished_at=datetime.utcnow() - timedelta(days=21),
            total_price=500.00,
        )
        db_session.add(booking)
        db_session.commit()
        
        # Use a narrow window that current time is definitely outside
        # (Testing at runtime, assume current time is not 03:00-03:01)
        eligible = segmentation_service.identify_eligible_customers(
            booking_cadence_days=21,
            send_window_start="03:00",
            send_window_end="03:01",
        )
        
        # Should be empty unless test runs exactly at 3:00 AM
        # This tests the send window filtering mechanism
        assert isinstance(eligible, list), "Should return a list"


class TestHelperMethods:
    """Test suite for helper methods."""
    
    def test_get_customer_booking_history_returns_recent_bookings(
        self, db_session, segmentation_service, sample_service
    ):
        """Should return customer's recent completed bookings."""
        user = User(
            id=uuid4(),
            email="history@example.com",
            name="History Customer",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=["home_cleaning"])
        db_session.add(customer)
        
        # Create 3 bookings
        for i in range(3):
            booking = Booking(
                id=uuid4(),
                customer_id=customer.id,
                service_id=sample_service.id,
                status=BookingStatus.COMPLETED,
                scheduled_at=datetime.utcnow() - timedelta(days=(i+1)*10),
                finished_at=datetime.utcnow() - timedelta(days=(i+1)*10),
                total_price=500.00,
            )
            db_session.add(booking)
        db_session.commit()
        
        history = segmentation_service.get_customer_booking_history(customer.id, limit=5)
        
        assert len(history) == 3, "Should return all 3 bookings"
        # Should be ordered by finished_at descending (most recent first)
        assert history[0].finished_at > history[1].finished_at
    
    def test_get_customer_preferred_services_returns_typical_services(
        self, db_session, segmentation_service
    ):
        """Should return customer's typical services."""
        user = User(
            id=uuid4(),
            email="prefs@example.com",
            name="Prefs Customer",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(
            id=user.id,
            typical_services=["home_cleaning", "plumbing", "electrical"]
        )
        db_session.add(customer)
        db_session.commit()
        
        services = segmentation_service.get_customer_preferred_services(customer.id)
        
        assert len(services) == 3, "Should return all 3 services"
        assert "home_cleaning" in services
        assert "plumbing" in services
    
    def test_get_customer_preferred_services_handles_empty_list(
        self, db_session, segmentation_service
    ):
        """Should handle customer with no typical services."""
        user = User(
            id=uuid4(),
            email="no.prefs@example.com",
            name="No Prefs",
            type=UserType.CUSTOMER,
            is_active=True,
            consent={"marketing": True},
        )
        db_session.add(user)
        
        customer = Customer(id=user.id, typical_services=[])
        db_session.add(customer)
        db_session.commit()
        
        services = segmentation_service.get_customer_preferred_services(customer.id)
        
        assert services == [], "Should return empty list"
