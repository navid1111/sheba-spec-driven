"""
Customer model - extends User for service consumers.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class Customer(Base):
    """
    Customer entity - service consumers (1:1 with User).
    """
    __tablename__ = "customers"
    
    # Primary key (also foreign key to users)
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Service preferences
    typical_services: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="Frequently booked service categories",
    )
    
    # Booking history
    last_booking_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    
    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, last_booking={self.last_booking_at})>"
