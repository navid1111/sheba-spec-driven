"""
Customer segmentation service for SmartEngage.

Identifies customers eligible for re-engagement reminders based on:
- Booking cadence (last booking X days ago)
- Send time window (only send during specific hours)
- Marketing consent
- Frequency caps (no spam)
"""
from datetime import datetime, timedelta, time
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from src.models.users import User
from src.models.customers import Customer
from src.models.bookings import Booking, BookingStatus
from src.models.ai_messages import AIMessage, MessageRole


class SegmentationService:
    """Service for identifying eligible customers for SmartEngage campaigns."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def identify_eligible_customers(
        self,
        booking_cadence_days: int = 21,
        send_window_start: str = "18:00",
        send_window_end: str = "20:00",
        cadence_tolerance_days: int = 1,
    ) -> list[UUID]:
        """
        Find customers eligible for re-engagement reminders.
        
        Args:
            booking_cadence_days: Days since last booking (e.g., 21 for 3-week cadence)
            send_window_start: Start time for sending messages (HH:MM format)
            send_window_end: End time for sending messages (HH:MM format)
            cadence_tolerance_days: Allow ±N days tolerance around cadence
        
        Returns:
            List of customer user_ids eligible for messages
        
        Eligibility Criteria:
        1. Has completed booking approximately X days ago (±tolerance)
        2. Current time is within send window
        3. Marketing consent enabled
        4. No message sent in last 24 hours (frequency cap)
        5. Customer record exists with booking history
        """
        # Check if current time is within send window
        if not self._is_within_send_window(send_window_start, send_window_end):
            return []
        
        # Calculate date range for booking cadence
        now = datetime.utcnow()
        target_booking_date = now - timedelta(days=booking_cadence_days)
        start_date = target_booking_date - timedelta(days=cadence_tolerance_days)
        end_date = target_booking_date + timedelta(days=cadence_tolerance_days)
        
        # Build query for eligible customers
        # Step 1: Get customers with completed bookings in the target date range
        eligible_bookings = (
            select(Booking.customer_id)
            .where(
                and_(
                    Booking.status == BookingStatus.COMPLETED,
                    Booking.finished_at >= start_date,
                    Booking.finished_at <= end_date,
                )
            )
            .distinct()
        )
        
        # Step 2: Filter by marketing consent
        # consent JSONB should have: {"marketing_consent": true}
        # Using PostgreSQL JSONB operators: (consent->>'marketing_consent')::boolean = true
        from sqlalchemy import cast, Boolean, literal
        
        customers_with_consent = (
            select(User.id)
            .join(Customer, Customer.id == User.id)
            .where(
                and_(
                    User.id.in_(eligible_bookings),
                    User.is_active == True,
                    # Check that marketing consent is explicitly true
                    func.coalesce(
                        cast(User.consent['marketing_consent'].astext, Boolean),
                        literal(False)
                    ) == True
                )
            )
        )
        
        # Step 3: Exclude customers who received a message in last 24 hours (frequency cap)
        frequency_cap_cutoff = now - timedelta(hours=24)
        recent_message_recipients = (
            select(AIMessage.user_id)
            .where(
                and_(
                    AIMessage.user_id.isnot(None),
                    AIMessage.role == MessageRole.CUSTOMER,
                    AIMessage.agent_type == "smartengage",
                    AIMessage.created_at >= frequency_cap_cutoff,
                )
            )
            .distinct()
        )
        
        # Final query: customers with consent minus those with recent messages
        eligible_customers_query = (
            select(User.id)
            .where(
                and_(
                    User.id.in_(customers_with_consent),
                    User.id.notin_(recent_message_recipients),
                )
            )
        )
        
        # Execute and return results
        result = self.db.execute(eligible_customers_query)
        customer_ids = [row[0] for row in result.fetchall()]
        
        return customer_ids
    
    def _is_within_send_window(
        self,
        window_start: str,
        window_end: str,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if current time falls within the send window.
        
        Args:
            window_start: Start time in HH:MM format (e.g., "18:00")
            window_end: End time in HH:MM format (e.g., "20:00")
            current_time: Optional datetime to check (defaults to now)
        
        Returns:
            True if current time is within window, False otherwise
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Parse time strings
        try:
            start_hour, start_minute = map(int, window_start.split(":"))
            end_hour, end_minute = map(int, window_end.split(":"))
        except (ValueError, AttributeError):
            # Invalid time format, default to False
            return False
        
        start_time = time(start_hour, start_minute)
        end_time = time(end_hour, end_minute)
        current_time_only = current_time.time()
        
        # Handle windows that cross midnight (e.g., 22:00 to 02:00)
        if start_time <= end_time:
            # Normal window (e.g., 18:00 to 20:00)
            return start_time <= current_time_only <= end_time
        else:
            # Window crosses midnight (e.g., 22:00 to 02:00)
            return current_time_only >= start_time or current_time_only <= end_time
    
    def get_last_booking(self, customer: Customer) -> Optional[Booking]:
        """
        Get the most recent completed booking for a customer.
        
        Args:
            customer: Customer object
        
        Returns:
            Most recent Booking or None if no bookings found
        """
        bookings = self.get_customer_booking_history(customer.id, limit=1)
        return bookings[0] if bookings else None
    
    def get_customer_booking_history(
        self,
        customer_id: UUID,
        limit: int = 5
    ) -> list[Booking]:
        """
        Get recent booking history for a customer.
        
        Args:
            customer_id: Customer UUID
            limit: Maximum number of bookings to return
        
        Returns:
            List of recent bookings, ordered by finished_at descending
        """
        query = (
            select(Booking)
            .where(
                and_(
                    Booking.customer_id == customer_id,
                    Booking.status == BookingStatus.COMPLETED,
                )
            )
            .order_by(Booking.finished_at.desc())
            .limit(limit)
        )
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_customer_preferred_services(
        self,
        customer_id: UUID
    ) -> list[str]:
        """
        Get customer's typical services from their profile.
        
        Args:
            customer_id: Customer UUID
        
        Returns:
            List of service category strings
        """
        query = select(Customer.typical_services).where(Customer.id == customer_id)
        result = self.db.execute(query)
        row = result.fetchone()
        
        return row[0] if row and row[0] else []
