"""
Worker model - extends User for service providers.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class Worker(Base):
    """
    Worker entity - service providers (1:1 with User).
    """
    __tablename__ = "workers"
    
    # Primary key (also foreign key to users)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Skills and experience
    skills: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Performance metrics
    rating_avg: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    total_jobs_completed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Work preferences
    preferred_areas: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
    )
    work_hours: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Work schedule: {mon: ['09:00-18:00'], ...}",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Coaching preferences
    opt_in_voice: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether worker has opted in for voice coaching",
    )
    
    def __repr__(self) -> str:
        return f"<Worker(id={self.id}, rating={self.rating_avg}, jobs={self.total_jobs_completed})>"
