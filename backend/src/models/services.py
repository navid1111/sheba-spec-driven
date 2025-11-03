"""
Service model - available services that can be booked.
"""
from uuid import uuid4
from typing import Optional
from uuid import UUID
import enum

from sqlalchemy import String, Numeric, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.lib.db import Base


class ServiceCategory(str, enum.Enum):
    """Service category enumeration."""
    CLEANING = "cleaning"
    BEAUTY = "beauty"
    ELECTRICAL = "electrical"
    OTHER = "other"


class Service(Base):
    """
    Service entity - bookable services.
    """
    __tablename__ = "services"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    
    # Service details
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[ServiceCategory] = mapped_column(
        SQLEnum(ServiceCategory, name="service_category"),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Pricing and duration
    base_price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name}, category={self.category})>"
