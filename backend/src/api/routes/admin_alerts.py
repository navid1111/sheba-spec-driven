"""
Admin Alerts API - Worker health monitoring endpoints.

Routes:
- GET /admin/alerts - List all active alerts
- GET /admin/alerts/{worker_id} - Get alerts for specific worker

Used by: Operations managers for proactive worker support (US3, FR-009)
"""
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.lib.db import get_db
from src.services.alerting_service import get_alerting_service, AlertingService
from src.lib.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/admin/alerts", tags=["admin_alerts"])


# Response Models
class AlertMetrics(BaseModel):
    """Metrics associated with an alert."""
    total_bookings: Optional[int] = None
    average_bookings: Optional[float] = None
    workload_ratio: Optional[float] = None
    avg_rating: Optional[float] = None
    current_rating: Optional[float] = None
    previous_rating: Optional[float] = None
    decline: Optional[float] = None
    threshold: Optional[float] = None


class Alert(BaseModel):
    """Individual alert details."""
    type: str = Field(..., description="Alert type (burnout, low_rating, quality_decline)")
    severity: str = Field(..., description="Severity level (low, medium, high, critical)")
    worker_id: str = Field(..., description="Worker UUID")
    worker_name: str = Field(..., description="Worker full name")
    worker_email: str = Field(..., description="Worker email")
    message: str = Field(..., description="Human-readable alert description")
    metrics: AlertMetrics = Field(..., description="Underlying metrics")
    created_at: str = Field(..., description="Alert creation timestamp (ISO 8601)")


class AlertsListResponse(BaseModel):
    """Response for alerts listing."""
    total: int = Field(..., description="Total number of alerts")
    alerts: List[Alert] = Field(..., description="List of alerts")


class WorkerAlertsResponse(BaseModel):
    """Response for worker-specific alerts."""
    worker_id: str = Field(..., description="Worker UUID")
    total: int = Field(..., description="Number of alerts for this worker")
    alerts: List[Alert] = Field(..., description="List of alerts")


# Routes
@router.get("", response_model=AlertsListResponse)
async def list_alerts(
    days: int = Query(30, ge=1, le=365, description="Days to look back for metrics"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    alert_type: Optional[str] = Query(None, description="Filter by type (burnout, low_rating, quality_decline)"),
    db: Session = Depends(get_db),
) -> AlertsListResponse:
    """
    List all active alerts across all workers.
    
    Args:
        days: Days to look back for metric calculation (default: 30)
        severity: Optional filter by severity level
        alert_type: Optional filter by alert type
        db: Database session
        
    Returns:
        AlertsListResponse with all matching alerts
    """
    logger.info(f"GET /admin/alerts (days={days}, severity={severity}, type={alert_type})")
    
    service = get_alerting_service(db)
    alerts_data = service.get_all_alerts(
        days=days,
        severity=severity,
        alert_type=alert_type,
    )
    
    alerts = [
        Alert(
            type=a['type'],
            severity=a['severity'],
            worker_id=a['worker_id'],
            worker_name=a['worker_name'],
            worker_email=a['worker_email'],
            message=a['message'],
            metrics=AlertMetrics(**a['metrics']),
            created_at=a['created_at'],
        )
        for a in alerts_data
    ]
    
    logger.info(f"Returning {len(alerts)} alerts")
    
    return AlertsListResponse(
        total=len(alerts),
        alerts=alerts,
    )


@router.get("/{worker_id}", response_model=WorkerAlertsResponse)
async def get_worker_alerts(
    worker_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Days to look back for metrics"),
    db: Session = Depends(get_db),
) -> WorkerAlertsResponse:
    """
    Get alerts for a specific worker.
    
    Args:
        worker_id: Worker UUID
        days: Days to look back for metric calculation (default: 30)
        db: Database session
        
    Returns:
        WorkerAlertsResponse with alerts for this worker
    """
    logger.info(f"GET /admin/alerts/{worker_id} (days={days})")
    
    service = get_alerting_service(db)
    alerts_data = service.get_worker_alerts(
        worker_id=worker_id,
        days=days,
    )
    
    alerts = [
        Alert(
            type=a['type'],
            severity=a['severity'],
            worker_id=a['worker_id'],
            worker_name=a['worker_name'],
            worker_email=a['worker_email'],
            message=a['message'],
            metrics=AlertMetrics(**a['metrics']),
            created_at=a['created_at'],
        )
        for a in alerts_data
    ]
    
    logger.info(f"Returning {len(alerts)} alerts for worker {worker_id}")
    
    return WorkerAlertsResponse(
        worker_id=str(worker_id),
        total=len(alerts),
        alerts=alerts,
    )
