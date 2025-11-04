"""
Booking model - service bookings between customers and workers.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class BookingStatus(str, enum.Enum):
    """Booking status state machine."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Booking(Base):
    """
    Booking entity - service appointments.
    State machine: pending → confirmed → in_progress → completed (or cancelled).
    """
    __tablename__ = "bookings"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Relationships
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Status
    status: Mapped[BookingStatus] = mapped_column(
        SQLEnum(BookingStatus, name="booking_status"),
        nullable=False,
        default=BookingStatus.PENDING,
        index=True,
    )
    
    # Timing
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Payment
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    
    # Deep link for SmartEngage
    deep_link_token: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        unique=True,
        comment="Short-lived token for deep link booking flow",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    __table_args__ = (
        CheckConstraint(
            "started_at IS NULL OR started_at >= scheduled_at",
            name="booking_start_after_schedule",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="booking_finish_after_start",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Booking(id={self.id}, status={self.status}, customer_id={self.customer_id})>"
