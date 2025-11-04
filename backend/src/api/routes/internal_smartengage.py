"""
Internal API routes for SmartEngage AI orchestration.

These endpoints are intended for internal service-to-service communication
and scheduled job triggers. They should be protected by internal authentication
in production deployments.

Endpoints:
- POST /internal/ai/smartengage/run-segment: Trigger SmartEngage campaign
"""
from typing import Optional, Literal
from uuid import UUID
import asyncio

from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel, Field

from src.jobs.campaign_runner import (
    run_smartengage_campaign,
    run_campaign_with_preset,
    CAMPAIGN_PRESETS,
)
from src.lib.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/internal/ai/smartengage", tags=["Internal AI"])


# Request/Response Models
class RunSegmentRequest(BaseModel):
    """Request payload for triggering SmartEngage campaign."""
    
    booking_cadence_days: Optional[int] = Field(
        default=21,
        ge=7,
        le=90,
        description="Days since last booking to target customers (7-90 days)"
    )
    send_window_start: Optional[int] = Field(
        default=9,
        ge=0,
        le=23,
        description="Hour to start sending (0-23, local time)"
    )
    send_window_end: Optional[int] = Field(
        default=18,
        ge=0,
        le=23,
        description="Hour to stop sending (0-23, local time)"
    )
    batch_size: Optional[int] = Field(
        default=50,
        ge=1,
        le=1000,
        description="Number of customers to process per batch"
    )
    promo_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional promo code to include in messages"
    )
    preset: Optional[Literal["default", "aggressive", "gentle", "weekend"]] = Field(
        default=None,
        description="Use predefined campaign configuration (overrides other params)"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "booking_cadence_days": 21,
                    "send_window_start": 9,
                    "send_window_end": 18,
                    "batch_size": 50,
                    "promo_code": "COMEBACK15"
                },
                {
                    "preset": "aggressive"
                }
            ]
        }


class RunSegmentResponse(BaseModel):
    """Response from triggering SmartEngage campaign."""
    
    status: Literal["started", "scheduled", "accepted"] = Field(
        default="started",
        description="Campaign execution status"
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracking campaign execution"
    )
    message: str = Field(
        default="SmartEngage campaign started",
        description="Human-readable status message"
    )
    campaign_result: Optional[dict] = Field(
        default=None,
        description="Campaign execution results (if completed synchronously)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "started",
                "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "SmartEngage campaign started successfully",
                "campaign_result": {
                    "total_eligible": 100,
                    "sent": 95,
                    "failed": 2,
                    "skipped": 3,
                    "duration_seconds": 12.5
                }
            }
        }


# Routes
@router.post(
    "/run-segment",
    response_model=RunSegmentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger SmartEngage Campaign",
    description="""
    Trigger a SmartEngage customer reminder campaign based on segment criteria.
    
    This endpoint executes the campaign synchronously and returns results.
    For large campaigns, consider using background job scheduling instead.
    
    **Authentication**: This endpoint should be protected by internal service tokens
    in production. Currently accessible for development/testing.
    
    **Presets**: Use the `preset` field to apply predefined configurations:
    - `default`: 21-day cadence, 50 batch size, no promo
    - `aggressive`: 14-day cadence, 100 batch size, COMEBACK15 promo
    - `gentle`: 28-day cadence, 25 batch size, no promo
    - `weekend`: 21-day cadence, WEEKEND20 promo
    """
)
async def run_segment(
    request: RunSegmentRequest,
    x_internal_token: Optional[str] = Header(
        default=None,
        description="Internal service authentication token (required in production)"
    )
):
    """
    Trigger SmartEngage campaign for eligible customers.
    
    Processes customers matching the segmentation criteria and sends
    personalized Bengali reminder messages with booking deep links.
    
    Args:
        request: Campaign parameters or preset name
        x_internal_token: Internal authentication token (optional for dev)
        
    Returns:
        Campaign execution status and results
        
    Raises:
        400: Invalid parameters or preset
        401: Invalid or missing internal token (production only)
        500: Campaign execution failed
    """
    try:
        # TODO: Add internal token validation in production
        # if settings.environment == "production" and not x_internal_token:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Internal authentication token required"
        #     )
        
        logger.info(
            "Internal API: SmartEngage campaign trigger received",
            extra={
                "preset": request.preset,
                "cadence_days": request.booking_cadence_days,
                "batch_size": request.batch_size,
                "has_promo": bool(request.promo_code),
            }
        )
        
        # Execute campaign based on preset or custom params
        if request.preset:
            logger.info(f"Using campaign preset: {request.preset}")
            campaign_result = await run_campaign_with_preset(request.preset)
        else:
            logger.info(
                f"Using custom campaign params: "
                f"cadence={request.booking_cadence_days}d, "
                f"window={request.send_window_start}-{request.send_window_end}h, "
                f"batch={request.batch_size}"
            )
            campaign_result = await run_smartengage_campaign(
                booking_cadence_days=request.booking_cadence_days,
                send_window_start=request.send_window_start,
                send_window_end=request.send_window_end,
                batch_size=request.batch_size,
                promo_code=request.promo_code,
            )
        
        # Extract correlation_id from result
        correlation_id = campaign_result.get("correlation_id")
        
        logger.info(
            f"SmartEngage campaign completed successfully "
            f"(correlation_id: {correlation_id}, "
            f"sent: {campaign_result.get('sent', 0)}/{campaign_result.get('total_eligible', 0)})"
        )
        
        return RunSegmentResponse(
            status="started",
            correlation_id=correlation_id,
            message="SmartEngage campaign completed successfully",
            campaign_result={
                "total_eligible": campaign_result.get("total_eligible", 0),
                "sent": campaign_result.get("sent", 0),
                "failed": campaign_result.get("failed", 0),
                "skipped": campaign_result.get("skipped", 0),
                "duration_seconds": campaign_result.get("duration_seconds", 0.0),
            }
        )
        
    except ValueError as e:
        # Invalid preset or parameters
        logger.error(f"Invalid campaign parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Campaign execution failed
        logger.error(
            f"SmartEngage campaign execution failed: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Campaign execution failed: {str(e)}"
        )
