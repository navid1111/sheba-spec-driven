"""
Consent and frequency cap utilities for notification system.

Provides functions to check:
1. User consent per channel (SMS, Push, WhatsApp, etc.)
2. Worker coaching consent (coaching_enabled flag)
3. Frequency caps to prevent spam (e.g., max N messages per day/week)
4. Opt-out management

For workers:
- General notifications (SMS/Email/Push): Use channel-based consent from User record
- CoachNova coaching: Check 'coaching_enabled' in consent JSONB
- Voice coaching: Check Worker.opt_in_voice field
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.logging import get_logger
from src.lib.config_flags import get_frequency_caps
from src.models.users import User
from src.models.workers import Worker
from src.models.ai_messages import AIMessage, MessageChannel, MessageRole

logger = get_logger(__name__)


# Legacy DEFAULT_CAPS for backward compatibility
# NOTE: Prefer using FrequencyCaps from config_flags for new code
DEFAULT_CAPS = {
    "sms_per_day": 3,
    "sms_per_week": 10,
    "push_per_day": 10,
    "push_per_week": 50,
    "whatsapp_per_day": 5,
    "whatsapp_per_week": 20,
}


def _get_caps_for_role(role: MessageRole, channel: MessageChannel, custom_caps: Optional[dict] = None) -> tuple[int, int]:
    """
    Get daily and weekly caps for a given role and channel.
    
    Uses FrequencyCaps configuration with channel-specific overrides.
    Falls back to custom_caps dict if provided (legacy support).
    
    Args:
        role: MessageRole (CUSTOMER or WORKER)
        channel: MessageChannel
        custom_caps: Optional custom caps dict (legacy)
        
    Returns:
        Tuple of (daily_cap, weekly_cap)
    """
    # If custom caps provided, use legacy logic
    if custom_caps is not None:
        channel_key = channel.value
        daily_cap = custom_caps.get(f"{channel_key}_per_day", 999)
        weekly_cap = custom_caps.get(f"{channel_key}_per_week", 999)
        return daily_cap, weekly_cap
    
    # Use FrequencyCaps configuration
    freq_caps = get_frequency_caps()
    
    # Get base limits for role
    if role == MessageRole.CUSTOMER:
        daily_cap = freq_caps.customer_daily_limit
        weekly_cap = freq_caps.customer_weekly_limit
    else:  # WORKER
        daily_cap = freq_caps.worker_daily_limit
        weekly_cap = freq_caps.worker_weekly_limit
    
    # Apply channel-specific overrides if set
    channel_key = channel.value
    if channel_key == "sms":
        daily_cap = freq_caps.sms_daily_limit or daily_cap
        weekly_cap = freq_caps.sms_weekly_limit or weekly_cap
    elif channel_key == "email":
        daily_cap = freq_caps.email_daily_limit or daily_cap
        weekly_cap = freq_caps.email_weekly_limit or weekly_cap
    elif channel_key == "app_push":
        daily_cap = freq_caps.push_daily_limit or daily_cap
        weekly_cap = freq_caps.push_weekly_limit or weekly_cap
    
    return daily_cap, weekly_cap


async def check_worker_coaching_consent(
    db: AsyncSession,
    worker_id: UUID,
) -> bool:
    """
    Check if worker has consented to receive CoachNova coaching interventions.
    
    This is a specialized consent check for worker performance coaching
    separate from general notification consent. Workers must explicitly
    opt-in to coaching via the 'coaching_enabled' flag in their consent.
    
    Args:
        db: AsyncSession
        worker_id: Worker ID
        
    Returns:
        True if worker has opted in to coaching, False otherwise
    """
    try:
        # Fetch worker's User record (workers are also users)
        stmt = select(User).where(User.id == worker_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for worker: {worker_id}")
            return False
        
        # Check coaching_enabled flag in consent JSONB
        consent = user.consent or {}
        coaching_enabled = consent.get('coaching_enabled', False)
        
        logger.info(
            f"Coaching consent check for worker",
            extra={
                "worker_id": str(worker_id),
                "coaching_enabled": coaching_enabled,
            }
        )
        
        return coaching_enabled
    
    except Exception as e:
        logger.error(f"Error checking worker coaching consent: {e}", exc_info=True)
        return False


async def check_worker_voice_consent(
    db: AsyncSession,
    worker_id: UUID,
) -> bool:
    """
    Check if worker has opted in to receive voice coaching.
    
    Voice coaching is optional and requires explicit opt-in via
    the Worker.opt_in_voice field.
    
    Args:
        db: AsyncSession
        worker_id: Worker ID
        
    Returns:
        True if worker has opted in to voice coaching, False otherwise
    """
    try:
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await db.execute(stmt)
        worker = result.scalar_one_or_none()
        
        if not worker:
            logger.warning(f"Worker not found: {worker_id}")
            return False
        
        voice_enabled = worker.opt_in_voice or False
        
        logger.info(
            f"Voice coaching consent check for worker",
            extra={
                "worker_id": str(worker_id),
                "voice_enabled": voice_enabled,
            }
        )
        
        return voice_enabled
    
    except Exception as e:
        logger.error(f"Error checking worker voice consent: {e}", exc_info=True)
        return False


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
    
    Uses FrequencyCaps configuration from config_flags with role-based and
    channel-specific limits. Supports legacy caps dict for backward compatibility.
    
    Args:
        db: Database session
        user_id: Customer user ID
        worker_id: Worker ID
        channel: Message channel
        role: Recipient role
        caps: Custom frequency caps dict (legacy, uses FrequencyCaps if None)
        
    Returns:
        Tuple of (allowed: bool, reason: Optional[str])
        - (True, None) if under cap
        - (False, "reason") if cap exceeded
    """
    # Determine which ID to use
    recipient_id = user_id if role == MessageRole.CUSTOMER else worker_id
    
    if not recipient_id:
        logger.warning("No recipient ID provided for frequency cap check")
        return False, "No recipient ID"
    
    try:
        # Get daily and weekly caps for this role/channel
        daily_cap, weekly_cap = _get_caps_for_role(role, channel, caps)
        
        channel_key = channel.value  # For logging
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


async def update_worker_coaching_consent(
    db: AsyncSession,
    worker_id: UUID,
    coaching_enabled: bool,
) -> bool:
    """
    Update worker's consent for CoachNova coaching interventions.
    
    Args:
        db: AsyncSession
        worker_id: Worker ID
        coaching_enabled: True to opt-in to coaching, False to opt-out
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        # Fetch worker's User record
        stmt = select(User).where(User.id == worker_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for worker: {worker_id}")
            return False
        
        # Update coaching_enabled in consent JSONB
        consent = user.consent or {}
        consent['coaching_enabled'] = coaching_enabled
        consent['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        user.consent = consent
        await db.commit()
        
        logger.info(
            f"Updated worker coaching consent",
            extra={
                "worker_id": str(worker_id),
                "coaching_enabled": coaching_enabled,
            }
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error updating worker coaching consent: {e}", exc_info=True)
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
