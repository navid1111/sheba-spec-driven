"""
Review model - customer feedback on completed bookings.
"""
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import String, Integer, ForeignKey, CheckConstraint, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class Review(Base):
    """
    Review entity - customer ratings and comments (1:1 with Booking).
    """
    __tablename__ = "reviews"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Relationship (one review per booking)
    booking_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    
    # Rating (1-5 scale)
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    # Comment
    comment: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )
    
    # Derived flags (e.g., late, rude, friendly)
    flags: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="Derived attributes like 'late', 'rude', 'friendly'",
    )
    
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="review_rating_range",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<Review(id={self.id}, booking_id={self.booking_id}, rating={self.rating})>"
