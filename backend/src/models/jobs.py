"""
Job model - scheduler bookkeeping for background tasks.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4, UUID
import enum

from sqlalchemy import String, Integer, BigInteger, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class JobType(str, enum.Enum):
    """Job type enumeration."""
    SNAPSHOT_DAILY = "snapshot_daily"
    CAMPAIGN_RUNNER = "campaign_runner"
    NOTIFIER = "notifier"
    OTHER = "other"


class JobStatus(str, enum.Enum):
    """Job execution status."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Job(Base):
    """
    Job entity - bookkeeping for scheduled background tasks.
    Uses Postgres advisory locks to prevent concurrent execution.
    """
    __tablename__ = "jobs"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Job classification
    type: Mapped[JobType] = mapped_column(
        SQLEnum(JobType, name="job_type"),
        nullable=False,
        index=True,
    )
    
    # Scheduling
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Execution
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    
    # Payload and lock
    payload: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Job-specific configuration and parameters",
    )
    lock_key: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Used with pg_try_advisory_lock for distributed locking",
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
        return f"<Job(id={self.id}, type={self.type}, status={self.status})>"
