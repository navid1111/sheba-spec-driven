"""
Admin routes for SmartEngage AI orchestration.

These endpoints allow admins to manually trigger SmartEngage campaigns
for specific customers or in bulk, bypassing scheduled job logic.

Endpoints:
- POST /admin/smartengage/send-single: Send reminder to specific customer
- POST /admin/smartengage/send-bulk: Send bulk reminders with custom criteria
"""
from typing import Optional, Literal, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.lib.db import get_db
from src.ai.smartengage import get_smartengage_orchestrator
from src.services.segmentation_service import SegmentationService
from src.lib.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/smartengage", tags=["Admin SmartEngage"])


# Request/Response Models
class SendSingleRequest(BaseModel):
    """Request payload for sending reminder to a specific customer."""
    
    customer_id: UUID = Field(
        ...,
        description="Customer UUID to send reminder to"
    )
    message_type: Literal["reminder", "promo", "custom"] = Field(
        ...,
        description="Message type: reminder (AI-generated), promo (with code), custom (admin message)"
    )
    promo_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Promo code to include (required for promo type)"
    )
    custom_message: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=500,
        description="Custom message text (required for custom type, will be safety filtered)"
    )
    ttl_hours: int = Field(
        default=48,
        ge=1,
        le=168,
        description="Deep link expiration time in hours (1-168, default 48)"
    )


class SendSingleResponse(BaseModel):
    """Response after sending single reminder."""
    
    success: bool = Field(
        ...,
        description="Whether message was sent successfully"
    )
    message_id: Optional[UUID] = Field(
        default=None,
        description="AIMessage ID if successful"
    )
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracking"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for failure if not successful"
    )


@router.post(
    "/send-single",
    response_model=SendSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Send reminder to specific customer",
    description="""
    Manually send a SmartEngage reminder to a specific customer.
    
    **Message Types:**
    - `reminder`: AI-generated message based on customer's booking history
    - `promo`: AI-generated message with promotional code included
    - `custom`: Admin-provided message (will be safety filtered)
    
    **Validation:**
    - `promo_code` is required when `message_type=promo`
    - `custom_message` is required when `message_type=custom`
    - Custom messages must pass safety filter or will be rejected
    
    **Response:**
    - `success=true`: Message sent, includes `message_id`
    - `success=false`: Message not sent, includes `reason`
    """
)
async def send_single_reminder(
    request: SendSingleRequest,
    db: Session = Depends(get_db)
) -> SendSingleResponse:
    """
    Send a single reminder to a specific customer.
    
    This endpoint allows admins to manually trigger reminder sends to
    individual customers, useful for:
    - Testing campaigns with specific users
    - Sending targeted promotional messages
    - Recovery actions for customers who missed automated campaigns
    - Custom outreach with admin-crafted messages
    
    Args:
        request: SendSingleRequest with customer_id and message parameters
        db: Database session
        
    Returns:
        SendSingleResponse with success status and message_id or reason
        
    Raises:
        HTTPException 400: Invalid request parameters
        HTTPException 404: Customer not found
        HTTPException 500: Orchestration failure
    """
    logger.info(
        f"Admin send-single request "
        f"(customer_id: {request.customer_id}, message_type: {request.message_type})"
    )
    
    # Validate message_type-specific requirements
    if request.message_type == "promo" and not request.promo_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="promo_code is required when message_type=promo"
        )
    
    if request.message_type == "custom" and not request.custom_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="custom_message is required when message_type=custom"
        )
    
    try:
        # Initialize orchestrator
        orchestrator = get_smartengage_orchestrator(db)
        
        # For "custom" message type, we need to handle it specially
        # For now, we'll use the standard reminder generation
        # TODO: Add support for custom message override in orchestrator
        
        # Generate and send reminder
        result = await orchestrator.generate_and_send_reminder(
            customer_id=request.customer_id,
            promo_code=request.promo_code,
            ttl_hours=request.ttl_hours,
        )
        
        logger.info(
            f"Admin send-single completed "
            f"(success: {result['success']}, correlation_id: {result['correlation_id']})"
        )
        
        return SendSingleResponse(
            success=result["success"],
            message_id=result.get("message_id"),
            correlation_id=result["correlation_id"],
            reason=result.get("reason"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Admin send-single failed (customer_id: {request.customer_id}): {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reminder send failed: {str(e)}"
        )


# Bulk Send Models and Endpoint
class SendBulkRequest(BaseModel):
    """Request payload for sending bulk reminders with custom criteria."""
    
    customer_ids: Optional[List[UUID]] = Field(
        default=None,
        description="Specific customer UUIDs to target (if provided, other filters ignored)"
    )
    booking_cadence_days: Optional[int] = Field(
        default=21,
        ge=7,
        le=90,
        description="Days since last booking to target customers (7-90 days)"
    )
    service_id: Optional[UUID] = Field(
        default=None,
        description="Filter customers by specific service they've booked"
    )
    send_window_start: Optional[int] = Field(
        default=0,
        ge=0,
        le=23,
        description="Hour to start sending (0-23, default 0 for immediate)"
    )
    send_window_end: Optional[int] = Field(
        default=23,
        ge=0,
        le=23,
        description="Hour to stop sending (0-23, default 23 for immediate)"
    )
    batch_size: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Number of customers to process per batch (1-1000)"
    )
    promo_code: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Promo code to include in all messages"
    )
    bypass_frequency_caps: bool = Field(
        default=False,
        description="Skip frequency cap checks (use with caution)"
    )


class BulkSendResult(BaseModel):
    """Individual result for bulk send."""
    
    customer_id: UUID
    success: bool
    message_id: Optional[UUID] = None
    reason: Optional[str] = None


class SendBulkResponse(BaseModel):
    """Response after sending bulk reminders."""
    
    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for tracking this bulk operation"
    )
    total_eligible: int = Field(
        ...,
        description="Total customers eligible for reminders"
    )
    sent: int = Field(
        ...,
        description="Number of messages successfully sent"
    )
    failed: int = Field(
        ...,
        description="Number of messages that failed to send"
    )
    skipped: int = Field(
        ...,
        description="Number of messages skipped (no consent, etc.)"
    )
    results: List[BulkSendResult] = Field(
        default_factory=list,
        description="Detailed results for each customer (limited to first 100)"
    )


@router.post(
    "/send-bulk",
    response_model=SendBulkResponse,
    status_code=status.HTTP_200_OK,
    summary="Send bulk reminders with custom criteria",
    description="""
    Send reminders to multiple customers based on custom filtering criteria.
    
    **Filtering Options:**
    - `customer_ids`: Target specific customers (overrides other filters)
    - `booking_cadence_days`: Target customers with bookings N days ago
    - `service_id`: Filter by specific service
    - `send_window_start/end`: Time window for sending (default 0-23 for immediate)
    
    **Options:**
    - `batch_size`: Control processing batch size (default 50)
    - `promo_code`: Include promotional code in all messages
    - `bypass_frequency_caps`: Skip 24h frequency cap check (use cautiously)
    
    **Response:**
    - Returns counts (total_eligible, sent, failed, skipped)
    - Includes detailed results for each customer (up to 100)
    - Use correlation_id to track operation
    """
)
async def send_bulk_reminders(
    request: SendBulkRequest,
    db: Session = Depends(get_db)
) -> SendBulkResponse:
    """
    Send bulk reminders to multiple customers.
    
    This endpoint provides flexible bulk sending capabilities for admins:
    - Target specific customer lists
    - Filter by booking patterns and services
    - Control batch processing and timing
    - Optionally bypass frequency caps for urgent campaigns
    
    Args:
        request: SendBulkRequest with filtering criteria
        db: Database session
        
    Returns:
        SendBulkResponse with operation results and detailed breakdown
        
    Raises:
        HTTPException 400: Invalid request parameters
        HTTPException 500: Bulk operation failure
    """
    from uuid import uuid4
    import asyncio
    
    correlation_id = uuid4()
    
    logger.info(
        f"Admin send-bulk request "
        f"(correlation_id: {correlation_id}, "
        f"customer_ids: {len(request.customer_ids) if request.customer_ids else 'None'}, "
        f"cadence: {request.booking_cadence_days})"
    )
    
    try:
        # Initialize services
        orchestrator = get_smartengage_orchestrator(db)
        
        # Determine eligible customers
        if request.customer_ids:
            # Use specific customer IDs provided
            eligible_customers = request.customer_ids
            logger.info(f"Using provided customer_ids: {len(eligible_customers)} customers")
        else:
            # Use segmentation service to find eligible customers
            segmentation = SegmentationService(db)
            
            # Convert hour integers to time strings for segmentation
            send_window_start_str = f"{request.send_window_start:02d}:00"
            send_window_end_str = f"{request.send_window_end:02d}:00"
            
            eligible_customers = segmentation.identify_eligible_customers(
                booking_cadence_days=request.booking_cadence_days,
                send_window_start=send_window_start_str,
                send_window_end=send_window_end_str,
            )
            
            # TODO: Add service_id filtering when implemented
            
            logger.info(f"Found {len(eligible_customers)} eligible customers via segmentation")
        
        total_eligible = len(eligible_customers)
        
        if total_eligible == 0:
            return SendBulkResponse(
                correlation_id=correlation_id,
                total_eligible=0,
                sent=0,
                failed=0,
                skipped=0,
                results=[]
            )
        
        # Process in batches
        results: List[BulkSendResult] = []
        sent = 0
        failed = 0
        skipped = 0
        
        for i in range(0, total_eligible, request.batch_size):
            batch = eligible_customers[i:i+request.batch_size]
            logger.info(f"Processing batch {i//request.batch_size + 1} ({len(batch)} customers)")
            
            # Process batch concurrently
            batch_tasks = [
                orchestrator.generate_and_send_reminder(
                    customer_id=customer_id,
                    promo_code=request.promo_code,
                    correlation_id=correlation_id,
                )
                for customer_id in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for customer_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    failed += 1
                    results.append(BulkSendResult(
                        customer_id=customer_id,
                        success=False,
                        reason=str(result)
                    ))
                elif result["success"]:
                    sent += 1
                    results.append(BulkSendResult(
                        customer_id=customer_id,
                        success=True,
                        message_id=result.get("message_id")
                    ))
                else:
                    skipped += 1
                    results.append(BulkSendResult(
                        customer_id=customer_id,
                        success=False,
                        reason=result.get("reason", "Unknown reason")
                    ))
        
        logger.info(
            f"Admin send-bulk completed "
            f"(correlation_id: {correlation_id}, "
            f"sent: {sent}/{total_eligible}, failed: {failed}, skipped: {skipped})"
        )
        
        # Limit results in response to first 100
        limited_results = results[:100]
        
        return SendBulkResponse(
            correlation_id=correlation_id,
            total_eligible=total_eligible,
            sent=sent,
            failed=failed,
            skipped=skipped,
            results=limited_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Admin send-bulk failed (correlation_id: {correlation_id}): {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk send failed: {str(e)}"
        )
