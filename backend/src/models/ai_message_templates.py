"""
AI Message Template model - versioned prompts for SmartEngage and CoachNova.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, Integer, Boolean, Text, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class AgentType(str, enum.Enum):
    """AI agent type enumeration."""
    SMARTENGAGE = "smartengage"
    COACHNOVA = "coachnova"


class AIMessageTemplate(Base):
    """
    AI Message Template entity - versioned prompts for AI agents.
    """
    __tablename__ = "ai_message_templates"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Agent configuration
    agent_type: Mapped[AgentType] = mapped_column(
        SQLEnum(AgentType, name="agent_type"),
        nullable=False,
        index=True,
    )
    trigger_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="e.g., renewal_reminder, punctuality_coaching",
    )
    
    # Template metadata
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Prompt content
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="System prompt for OpenAI",
    )
    example_user_context: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Example context JSON for testing",
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
        return f"<AIMessageTemplate(id={self.id}, agent={self.agent_type}, version={self.version})>"
