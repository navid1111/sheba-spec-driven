"""
Consent and frequency cap utilities for notification system.

Provides functions to check:
1. User consent per channel (SMS, Push, WhatsApp, etc.)
2. Frequency caps to prevent spam (e.g., max N messages per day/week)
3. Opt-out management
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.logging import get_logger
from src.models.users import User
from src.models.workers import Worker
from src.models.ai_messages import AIMessage, MessageChannel, MessageRole

logger = get_logger(__name__)


# Frequency cap limits (configurable)
DEFAULT_CAPS = {
    "sms_per_day": 3,
    "sms_per_week": 10,
    "push_per_day": 10,
    "push_per_week": 50,
    "whatsapp_per_day": 5,
    "whatsapp_per_week": 20,
}


async def check_consent(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None,
    channel: MessageChannel = MessageChannel.SMS,
    role: MessageRole = MessageRole.CUSTOMER,
) -> bool:
    """
    Check if user/worker has consented to receive messages on the given channel.
    
    Args:
        db: Database session
        user_id: Customer user ID
        worker_id: Worker ID
        channel: Message channel (SMS, PUSH, WHATSAPP, etc.)
        role: Recipient role (CUSTOMER or WORKER)
        
    Returns:
        True if consent granted, False otherwise
    """
    # Determine which ID to use
    recipient_id = user_id if role == MessageRole.CUSTOMER else worker_id
    
    if not recipient_id:
        logger.warning("No recipient ID provided for consent check")
        return False
    
    try:
        # Fetch user/worker based on role
        if role == MessageRole.CUSTOMER:
            stmt = select(User).where(User.id == recipient_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User not found: {recipient_id}")
                return False
            
            # Check consent field (JSONB)
            consent = user.consent or {}
            channel_key = channel.value  # e.g., "sms", "push", "whatsapp"
            
            # Get consent status (default to False for privacy)
            has_consent = consent.get(channel_key, False)
            
            logger.info(
                f"Consent check for user",
                extra={
                    "user_id": str(recipient_id),
                    "channel": channel_key,
                    "consented": has_consent,
                }
            )
            
            return has_consent
        
        else:  # WORKER
            # For workers, check opt_in_voice for voice channels
            # For other channels, use user's consent from the linked User record
            stmt = select(Worker).where(Worker.id == recipient_id)
            result = await db.execute(stmt)
            worker = result.scalar_one_or_none()
            
            if not worker:
                logger.warning(f"Worker not found: {recipient_id}")
                return False
            
            # Get the linked User record for general consent
            user_stmt = select(User).where(User.id == worker.id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User record not found for worker: {recipient_id}")
                return False
            
            # Check consent from User record
            consent = user.consent or {}
            channel_key = channel.value
            has_consent = consent.get(channel_key, False)
            
            logger.info(
                f"Consent check for worker",
                extra={
                    "worker_id": str(recipient_id),
                    "channel": channel_key,
                    "consented": has_consent,
                }
            )
            
            return has_consent
    
    except Exception as e:
        logger.error(f"Error checking consent: {e}", exc_info=True)
        return False


async def check_frequency_cap(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None,
    channel: MessageChannel = MessageChannel.SMS,
    role: MessageRole = MessageRole.CUSTOMER,
    caps: Optional[dict] = None,
) -> tuple[bool, Optional[str]]:
    """
    Check if sending a message would exceed frequency caps.
    
    Args:
        db: Database session
        user_id: Customer user ID
        worker_id: Worker ID
        channel: Message channel
        role: Recipient role
        caps: Custom frequency caps (uses DEFAULT_CAPS if None)
        
    Returns:
        Tuple of (allowed: bool, reason: Optional[str])
        - (True, None) if under cap
        - (False, "reason") if cap exceeded
    """
    # Use default caps if not provided
    if caps is None:
        caps = DEFAULT_CAPS
    
    # Determine which ID to use
    recipient_id = user_id if role == MessageRole.CUSTOMER else worker_id
    
    if not recipient_id:
        logger.warning("No recipient ID provided for frequency cap check")
        return False, "No recipient ID"
    
    try:
        # Get channel-specific caps
        channel_key = channel.value  # e.g., "sms", "push"
        daily_cap = caps.get(f"{channel_key}_per_day", 999)
        weekly_cap = caps.get(f"{channel_key}_per_week", 999)
        
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        # Build base query
        base_filter = [
            AIMessage.channel == channel,
            AIMessage.created_at >= week_ago,  # Look at last 7 days
        ]
        
        # Add recipient filter
        if role == MessageRole.CUSTOMER:
            base_filter.append(AIMessage.user_id == recipient_id)
        else:
            base_filter.append(AIMessage.worker_id == recipient_id)
        
        # Count messages in last 24 hours
        daily_stmt = (
            select(func.count(AIMessage.id))
            .where(*base_filter, AIMessage.created_at >= day_ago)
        )
        daily_result = await db.execute(daily_stmt)
        daily_count = daily_result.scalar() or 0
        
        if daily_count >= daily_cap:
            reason = f"Daily cap exceeded: {daily_count}/{daily_cap} messages in last 24h"
            logger.warning(
                reason,
                extra={
                    "recipient_id": str(recipient_id),
                    "channel": channel_key,
                    "role": role.value,
                }
            )
            return False, reason
        
        # Count messages in last 7 days
        weekly_stmt = select(func.count(AIMessage.id)).where(*base_filter)
        weekly_result = await db.execute(weekly_stmt)
        weekly_count = weekly_result.scalar() or 0
        
        if weekly_count >= weekly_cap:
            reason = f"Weekly cap exceeded: {weekly_count}/{weekly_cap} messages in last 7 days"
            logger.warning(
                reason,
                extra={
                    "recipient_id": str(recipient_id),
                    "channel": channel_key,
                    "role": role.value,
                }
            )
            return False, reason
        
        # Under cap
        logger.info(
            f"Frequency cap check passed",
            extra={
                "recipient_id": str(recipient_id),
                "channel": channel_key,
                "daily": f"{daily_count}/{daily_cap}",
                "weekly": f"{weekly_count}/{weekly_cap}",
            }
        )
        
        return True, None
    
    except Exception as e:
        logger.error(f"Error checking frequency cap: {e}", exc_info=True)
        return False, f"Error checking frequency cap: {str(e)}"


async def update_consent(
    db: AsyncSession,
    user_id: UUID,
    channel: MessageChannel,
    consented: bool,
) -> bool:
    """
    Update user consent for a specific channel.
    
    Args:
        db: Database session
        user_id: User ID
        channel: Message channel
        consented: True to opt-in, False to opt-out
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        # Fetch user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return False
        
        # Update consent
        consent = user.consent or {}
        channel_key = channel.value
        consent[channel_key] = consented
        consent["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        user.consent = consent
        await db.commit()
        
        logger.info(
            f"Updated consent",
            extra={
                "user_id": str(user_id),
                "channel": channel_key,
                "consented": consented,
            }
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating consent: {e}", exc_info=True)
        await db.rollback()
        return False


async def can_send_notification(
    db: AsyncSession,
    user_id: Optional[UUID] = None,
    worker_id: Optional[UUID] = None,
    channel: MessageChannel = MessageChannel.SMS,
    role: MessageRole = MessageRole.CUSTOMER,
    caps: Optional[dict] = None,
) -> tuple[bool, Optional[str]]:
    """
    Combined check: consent + frequency cap.
    
    This is the main function to call before sending any notification.
    
    Args:
        db: Database session
        user_id: Customer user ID
        worker_id: Worker ID
        channel: Message channel
        role: Recipient role
        caps: Custom frequency caps
        
    Returns:
        Tuple of (allowed: bool, reason: Optional[str])
        - (True, None) if allowed to send
        - (False, "reason") if blocked
    """
    # Check consent first (faster, no DB aggregation)
    has_consent = await check_consent(
        db=db,
        user_id=user_id,
        worker_id=worker_id,
        channel=channel,
        role=role,
    )
    
    if not has_consent:
        return False, f"User has not consented to {channel.value} notifications"
    
    # Check frequency cap
    under_cap, cap_reason = await check_frequency_cap(
        db=db,
        user_id=user_id,
        worker_id=worker_id,
        channel=channel,
        role=role,
        caps=caps,
    )
    
    if not under_cap:
        return False, cap_reason
    
    # All checks passed
    return True, None
