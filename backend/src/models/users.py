"""
User model - base entity for customers, workers, and admins.
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, Enum as SQLEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import enum

from src.lib.db import Base


class UserType(str, enum.Enum):
    """User type enumeration."""
    CUSTOMER = "customer"
    WORKER = "worker"
    ADMIN = "admin"


class User(Base):
    """
    User entity - represents all system users.
    Either phone or email must be present.
    """
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Contact info (at least one required)
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )
    
    # Profile
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[UserType] = mapped_column(
        SQLEnum(UserType, name="user_type"),
        nullable=False,
        index=True,
    )
    
    # Location
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Preferences
    language_preference: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="bn",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Consent per channel (JSONB: {push: true, sms: false, whatsapp: false, updated_at: ...})
    consent: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"push": True, "sms": False, "whatsapp": False},
    )
    
    # Additional metadata (using extra_data to avoid SQLAlchemy reserved name)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        name="metadata",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    __table_args__ = (
        CheckConstraint(
            "phone IS NOT NULL OR email IS NOT NULL",
            name="user_contact_required",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, type={self.type})>"
