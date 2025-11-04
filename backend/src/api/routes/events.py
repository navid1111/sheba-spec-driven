"""
User events tracking endpoint.

Captures user interactions like message opens, clicks, deeplink follows, etc.
Used for analytics, attribution, and campaign effectiveness measurement.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_current_user
from src.lib.logging import get_logger
from src.lib.metrics import get_metrics_collector
from src.models.user_activity_events import (
    UserActivityEvent,
    EventType,
    EventSource,
)
from src.models.users import User


logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


class UserEventRequest(BaseModel):
    """User event ingestion request."""
    event_type: str = Field(..., description="Type of event (message_clicked, notification_opened, etc.)")
    source: Optional[str] = Field(default="app", description="Event source (push, sms, app, web)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional event metadata")
    correlation_id: Optional[UUID] = Field(default=None, description="Correlation ID for tracing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "message_clicked",
                "source": "push",
                "metadata": {
                    "ai_message_id": "550e8400-e29b-41d4-a716-446655440000",
                    "campaign_id": "smartengage_reminder",
                    "deeplink_token": "eyJhbGciOiJIUzI1NiIs...",
                },
                "correlation_id": "660e8400-e29b-41d4-a716-446655440000"
            }
        }


class UserEventResponse(BaseModel):
    """User event response."""
    status: str = Field(..., description="Status of event ingestion")
    event_id: UUID = Field(..., description="ID of created event")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "event_id": "770e8400-e29b-41d4-a716-446655440000"
            }
        }


@router.post(
    "",
    response_model=UserEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest user activity event",
    description="""
    Track user interactions and events for analytics and attribution.
    
    Common event types:
    - `message_clicked`: User clicked on a message or notification
    - `notification_opened`: User opened a push/SMS notification
    - `deeplink_followed`: User followed a deeplink from a message
    - `booking_created`: User created a booking from a campaign
    - `app_open`: User opened the app
    
    The metadata field can contain additional context:
    - `ai_message_id`: Reference to the AI message that triggered this event
    - `campaign_id`: Campaign identifier
    - `deeplink_token`: Token from deeplink (for attribution)
    - `screen_name`: Screen or page name
    - `device`: Device information
    
    Events are used for:
    - Campaign effectiveness measurement
    - Attribution (message → booking conversion)
    - User behavior analytics
    - A/B testing and optimization
    """
)
async def ingest_event(
    request: UserEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserEventResponse:
    """
    Ingest user activity event.
    
    Args:
        request: Event details
        db: Database session
        current_user: Authenticated user from JWT
        
    Returns:
        Event confirmation with ID
    """
    # Validate event_type (accept any string, will map to enum if possible)
    try:
        # Try to map to EventType enum
        event_type_enum = EventType(request.event_type.lower())
    except ValueError:
        # If not in enum, use a generic type or extend enum
        logger.warning(
            f"Unknown event_type received: {request.event_type}",
            extra={"user_id": str(current_user.id), "event_type": request.event_type}
        )
        # Default to app_open for unknown types (could be extended later)
        event_type_enum = EventType.APP_OPEN
    
    # Validate source
    try:
        source_enum = EventSource(request.source.lower() if request.source else "app")
    except ValueError:
        logger.warning(
            f"Unknown source received: {request.source}",
            extra={"user_id": str(current_user.id), "source": request.source}
        )
        source_enum = EventSource.APP
    
    # Create event record
    event = UserActivityEvent(
        user_id=current_user.id,
        event_type=event_type_enum,
        source=source_enum,
        event_metadata=request.metadata,
        correlation_id=request.correlation_id,
        occurred_at=datetime.now(timezone.utc),
    )
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Track metrics for opens, clicks, and conversions
    metrics = get_metrics_collector()
    metadata = request.metadata or {}
    
    # Determine agent_type and channel from metadata
    agent_type = metadata.get("agent_type", "unknown")
    channel = metadata.get("channel", "UNKNOWN")
    
    # Increment appropriate counter based on event type
    if event_type_enum == EventType.NOTIFICATION_OPENED:
        metrics.increment_opens(agent_type=agent_type, channel=channel, source=source_enum.value)
    elif event_type_enum == EventType.MESSAGE_CLICKED:
        metrics.increment_clicks(agent_type=agent_type, channel=channel, source=source_enum.value)
    elif event_type_enum == EventType.BOOKING_CREATED:
        metrics.increment_conversions(agent_type=agent_type, channel=channel, conversion_type="booking_created")
    elif event_type_enum == EventType.DEEPLINK_FOLLOWED:
        metrics.increment_conversions(agent_type=agent_type, channel=channel, conversion_type="deeplink_followed")
    
    logger.info(
        f"User event ingested",
        extra={
            "event_id": str(event.id),
            "user_id": str(current_user.id),
            "event_type": event_type_enum.value,
            "correlation_id": str(request.correlation_id) if request.correlation_id else None,
        }
    )
    
    return UserEventResponse(
        status="accepted",
        event_id=event.id
    )
