"""
User Activity Event model - tracking user interactions and events.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class EventType(str, enum.Enum):
    """User event type enumeration."""
    APP_OPEN = "app_open"
    BOOKING_CREATED = "booking_created"
    MESSAGE_CLICKED = "message_clicked"
    NOTIFICATION_OPENED = "notification_opened"
    DEEPLINK_FOLLOWED = "deeplink_followed"
    BOOKING_COMPLETED = "booking_completed"
    REVIEW_SUBMITTED = "review_submitted"
    WORKER_SHIFT_START = "worker_shift_start"
    WORKER_SHIFT_END = "worker_shift_end"


class EventSource(str, enum.Enum):
    """Event source/origin."""
    PUSH = "push"
    SMS = "sms"
    APP = "app"
    WEB = "web"
    SYSTEM = "system"


class UserActivityEvent(Base):
    """
    User Activity Event entity - tracks all user interactions.
    """
    __tablename__ = "user_activity_events"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # User reference
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Event classification
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType, name="event_type"),
        nullable=False,
        index=True,
    )
    source: Mapped[EventSource] = mapped_column(
        SQLEnum(EventSource, name="event_source"),
        nullable=False,
    )
    
    # Event metadata (campaign_id, screen_name, device, ai_message_id, etc.)
    event_metadata: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        name="metadata",
    )
    
    # Correlation for tracing
    correlation_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    
    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    
    def __repr__(self) -> str:
        return f"<UserActivityEvent(id={self.id}, user_id={self.user_id}, type={self.event_type})>"
