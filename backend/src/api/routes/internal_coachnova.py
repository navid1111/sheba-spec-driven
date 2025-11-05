"""
Internal API routes for CoachNova AI orchestration.

These endpoints are intended for internal service-to-service communication
and scheduled job triggers. They should be protected by internal authentication
in production deployments.

Endpoints:
- POST /internal/ai/coachnova/run-for-worker/{worker_id}: Trigger CoachNova coaching
"""
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.lib.logging import get_logger
from src.services.performance_service import PerformanceService
from src.ai.coachnova import CoachNovaOrchestrator
from src.models.workers import Worker
from sqlalchemy import select

logger = get_logger(__name__)

router = APIRouter(prefix="/internal/ai/coachnova", tags=["Internal AI"])


# Request/Response Models
class RunForWorkerRequest(BaseModel):
    """Request payload for triggering CoachNova coaching."""
    
    dry_run: Optional[bool] = Field(
        default=False,
        description="If true, validate eligibility but don't send message"
    )
    force: Optional[bool] = Field(
        default=False,
        description="If true, bypass frequency caps (for testing)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "dry_run": False,
                "force": False
            }
        }


class RunForWorkerResponse(BaseModel):
    """Response from triggering CoachNova coaching."""
    
    success: bool = Field(
        ...,
        description="Whether coaching was successfully triggered or validated"
    )
    message_id: Optional[UUID] = Field(
        default=None,
        description="ID of created coaching message (if sent)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for failure or skip (if success=false)"
    )
    correlation_id: Optional[UUID] = Field(
        default=None,
        description="Correlation ID for tracking coaching flow"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "correlation_id": "456e7890-e89b-12d3-a456-426614174001"
            }
        }


# Routes
@router.post(
    "/run-for-worker/{worker_id}",
    response_model=RunForWorkerResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger CoachNova Coaching for Worker",
    description="""
    Trigger CoachNova coaching intervention for a specific worker.
    
    This endpoint:
    1. Validates worker exists
    2. Checks performance signals (late arrivals, ratings, workload)
    3. Validates consent and eligibility
    4. Generates Bengali coaching message
    5. Creates AIMessage record and triggers notification
    
    **Authentication**: This endpoint should be protected by internal service tokens
    in production. Currently accessible for development/testing.
    """
)
async def run_for_worker(
    worker_id: UUID,
    request: Optional[RunForWorkerRequest] = None,
    db: Session = Depends(get_db),
    x_internal_token: Optional[str] = Header(
        default=None,
        description="Internal service authentication token (required in production)"
    )
):
    """
    Trigger CoachNova coaching for a specific worker.
    
    Checks worker performance signals, consent, and eligibility, then
    generates personalized Bengali coaching message with actionable advice.
    
    Args:
        worker_id: UUID of worker to coach
        request: Optional parameters (dry_run, force)
        db: Database session
        x_internal_token: Internal authentication token (optional for dev)
        
    Returns:
        Coaching execution status with message_id or reason
        
    Raises:
        404: Worker not found
        500: Coaching execution failed
    """
    try:
        # TODO: Add internal token validation in production
        # if settings.environment == "production" and not x_internal_token:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Internal authentication token required"
        #     )
        
        # Handle None request body (when no body provided)
        if request is None:
            request = RunForWorkerRequest()
        
        logger.info(
            "Internal API: CoachNova coaching trigger received",
            extra={
                "worker_id": str(worker_id),
                "dry_run": request.dry_run,
                "force": request.force,
            }
        )
        
        # Generate correlation ID for tracking
        correlation_id = uuid4()
        
        # T047: Validate worker exists and get performance signals
        stmt = select(Worker).where(Worker.id == worker_id)
        result = db.execute(stmt)
        worker = result.scalar_one_or_none()
        
        if not worker:
            logger.warning(f"Worker not found: {worker_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Worker not found: {worker_id}"
            )
        
        # Get performance signals to determine eligibility (sync version)
        performance_signals = PerformanceService.get_signals_sync(worker_id, db)
        
        if not performance_signals.get("eligible_for_coaching", False):
            logger.info(
                f"Worker not eligible for coaching (correlation_id: {correlation_id})",
                extra={
                    "worker_id": str(worker_id),
                    "issues": performance_signals.get("issues", [])
                }
            )
            return RunForWorkerResponse(
                success=False,
                message_id=None,
                reason="Worker not eligible: no performance issues detected",
                correlation_id=correlation_id
            )
        
        # T048: CoachNova orchestrator - generate coaching message (sync)
        orchestrator = CoachNovaOrchestrator()
        result = orchestrator.generate_coaching_sync(
            worker_id=worker_id,
            performance_signals=performance_signals,
            correlation_id=correlation_id,
            db=db,
            dry_run=request.dry_run,
            force=request.force
        )
        
        if result["success"]:
            logger.info(
                f"CoachNova coaching completed successfully (correlation_id: {correlation_id})",
                extra={
                    "worker_id": str(worker_id),
                    "message_id": str(result.get("message_id")),
                    "dry_run": request.dry_run
                }
            )
            return RunForWorkerResponse(
                success=True,
                message_id=result.get("message_id"),
                reason=None,
                correlation_id=correlation_id
            )
        else:
            logger.warning(
                f"CoachNova coaching skipped (correlation_id: {correlation_id})",
                extra={
                    "worker_id": str(worker_id),
                    "reason": result.get("reason")
                }
            )
            return RunForWorkerResponse(
                success=False,
                message_id=None,
                reason=result.get("reason"),
                correlation_id=correlation_id
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions (404, 401, etc.)
        raise
    except Exception as e:
        # Coaching execution failed
        logger.error(
            f"CoachNova coaching execution failed: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coaching execution failed: {str(e)}"
        )
