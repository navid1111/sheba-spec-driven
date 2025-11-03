"""
Campaign model - AI engagement campaigns (SmartEngage, CoachNova).
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class CampaignType(str, enum.Enum):
    """Campaign type enumeration."""
    SMARTENGAGE = "smartengage"
    COACHNOVA = "coachnova"


class CampaignStatus(str, enum.Enum):
    """Campaign execution status."""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Campaign(Base):
    """
    Campaign entity - orchestrated AI engagement runs.
    """
    __tablename__ = "campaigns"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Campaign classification
    type: Mapped[CampaignType] = mapped_column(
        SQLEnum(CampaignType, name="campaign_type"),
        nullable=False,
        index=True,
    )
    
    # Execution
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus, name="campaign_status"),
        nullable=False,
        default=CampaignStatus.SCHEDULED,
        index=True,
    )
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    # Targeting and configuration
    filters: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="User segmentation filters",
    )
    feature_flag: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Feature flag for canary rollouts",
    )
    
    # Results tracking
    stats: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Campaign statistics: {users_targeted, users_reached, conversions, ...}",
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
        return f"<Campaign(id={self.id}, type={self.type}, status={self.status})>"
