"""
Services API routes.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.lib.db import get_db
from src.models.services import Service, ServiceCategory


# Pydantic schemas
class ServiceResponse(BaseModel):
    """Service response schema matching OpenAPI contract."""
    id: UUID
    name: str
    category: str
    description: Optional[str] = None
    base_price: float
    duration_minutes: int
    active: bool = True
    
    model_config = {"from_attributes": True}


# Router
router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=List[ServiceResponse])
def list_services(
    category: Optional[ServiceCategory] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Show only active services"),
    db: Session = Depends(get_db),
) -> List[ServiceResponse]:
    """
    List available services.
    
    Query parameters:
    - category: Filter by service category (cleaning, beauty, electrical, other)
    - active_only: Show only active services (default: true)
    
    Returns:
        List of services matching the filters
    """
    # Build query
    stmt = select(Service)
    
    # Apply filters
    if active_only:
        stmt = stmt.where(Service.active == True)
    
    if category:
        stmt = stmt.where(Service.category == category)
    
    # Order by category and name
    stmt = stmt.order_by(Service.category, Service.name)
    
    # Execute query
    result = db.execute(stmt)
    services = result.scalars().all()
    
    # Convert to response schema
    return [
        ServiceResponse(
            id=s.id,
            name=s.name,
            category=s.category.value,  # Convert enum to string
            description=s.description,
            base_price=float(s.base_price),
            duration_minutes=s.duration_minutes,
            active=s.active,
        )
        for s in services
    ]
