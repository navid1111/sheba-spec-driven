"""
AI Message model - generated messages for customers and workers.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class MessageRole(str, enum.Enum):
    """Message recipient role."""
    CUSTOMER = "customer"
    WORKER = "worker"


class MessageChannel(str, enum.Enum):
    """Delivery channel enumeration."""
    SMS = "sms"
    EMAIL = "email"
    APP_PUSH = "app_push"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class MessageType(str, enum.Enum):
    """Message type/purpose."""
    REMINDER = "reminder"
    COACHING = "coaching"
    BURNOUT_CHECK = "burnout_check"
    UPSELL = "upsell"


class DeliveryStatus(str, enum.Enum):
    """Message delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class UserResponse(str, enum.Enum):
    """User interaction with message."""
    CLICKED = "clicked"
    REPLIED = "replied"
    IGNORED = "ignored"
    BOOKED = "booked"
    ACKNOWLEDGED = "acknowledged"


class AIMessage(Base):
    """
    AI Message entity - generated and delivered messages.
    """
    __tablename__ = "ai_messages"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Recipient (one of user_id or worker_id should be set)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    worker_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    
    # Message classification
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, name="message_role"),
        nullable=False,
    )
    agent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="smartengage or coachnova",
    )
    channel: Mapped[MessageChannel] = mapped_column(
        SQLEnum(MessageChannel, name="message_channel"),
        nullable=False,
    )
    message_type: Mapped[MessageType] = mapped_column(
        SQLEnum(MessageType, name="message_type"),
        nullable=False,
    )
    
    # Content
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="bn",
    )
    
    # Delivery tracking
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        SQLEnum(DeliveryStatus, name="delivery_status"),
        nullable=False,
        default=DeliveryStatus.PENDING,
        index=True,
    )
    
    # User interaction
    user_response: Mapped[Optional[UserResponse]] = mapped_column(
        SQLEnum(UserResponse, name="user_response"),
        nullable=True,
    )
    
    # Template and generation metadata
    template_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_message_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    correlation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
        default=uuid4,
    )
    
    # AI generation details
    model: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="OpenAI model used (e.g., gpt-4o-mini)",
    )
    prompt_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    safety_checks: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Safety filter results",
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
    
    def __repr__(self) -> str:
        return f"<AIMessage(id={self.id}, agent={self.agent_type}, status={self.delivery_status})>"
