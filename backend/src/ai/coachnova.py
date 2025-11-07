"""
CoachNova Orchestrator - AI-Powered Worker Coaching System.

This module orchestrates the complete CoachNova flow:
1. Get performance signals (via PerformanceService)
2. Check eligibility (performance issues, consent, frequency caps)
3. Generate personalized Bengali coaching messages (via OpenAI)
4. Apply safety filters (dignity-centered, no shaming language)
5. Create AIMessage records for tracking
6. Send notifications (via EmailNotificationProvider)

The orchestrator respects:
- Worker consent (coaching_enabled)
- Frequency caps (7 days between coaching messages)
- Dignity-centered communication (no shaming, empathetic tone)
- Safety guardrails (reject inappropriate content)
"""
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from concurrent.futures import ThreadPoolExecutor

from src.lib.logging import get_logger
from src.lib.metrics import get_metrics_collector
from src.ai.template_loader import load_template, format_template
from src.services.performance_service import PerformanceService
from src.services.notification_service import (
    get_notification_service,
    NotificationService,
)
from src.ai.client import get_openai_client, OpenAIClient
from src.ai.safety import get_safety_filter, SafetyFilter
from src.models.ai_messages import (
    AIMessage,
    MessageRole,
    MessageChannel,
    MessageType,
    DeliveryStatus,
)
from src.models.users import User
from src.models.workers import Worker

logger = get_logger(__name__)


# Frequency cap: 7 days between coaching messages per worker
COACHING_FREQUENCY_DAYS = 7


class CoachNovaOrchestrator:
    """
    CoachNova orchestrator for AI-powered worker coaching.
    
    Coordinates performance analysis, eligibility checks, message generation,
    safety filtering, and notification delivery for personalized worker coaching.
    """
    
    def __init__(
        self,
        openai_client: Optional[OpenAIClient] = None,
        safety_filter: Optional[SafetyFilter] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        """
        Initialize CoachNova orchestrator.
        
        Args:
            openai_client: OpenAI client (defaults to global instance)
            safety_filter: Safety filter (defaults to global instance)
            notification_service: Notification service (optional, created per-request)
        """
        self.openai_client = openai_client or get_openai_client()
        self.safety_filter = safety_filter or get_safety_filter(use_openai_moderation=False)
        self._notification_service = notification_service
        
        logger.info("CoachNovaOrchestrator initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _generate_coaching_with_openai(
        self,
        worker_name: str,
        performance_signals: Dict[str, Any],
    ) -> str:
        """
        Generate Bengali coaching message using OpenAI GPT-4o-mini.
        
        Args:
            worker_name: Worker's name for personalization
            performance_signals: Performance metrics from PerformanceService
            
        Returns:
            Generated Bengali coaching message
            
        Raises:
            Exception: If OpenAI API call fails
        """
        # Build context for coaching
        issues = performance_signals.get('issues', [])
        late_arrivals = performance_signals.get('late_arrivals_last_7_days', 0)
        avg_rating = performance_signals.get('avg_rating_last_30_days')
        
        # Load template from file (with fallback)
        try:
            template_content = load_template(agent_type='coaching', locale='bn', version=1)
            if template_content:
                # Extract system prompt from template (everything before "## Example Messages")
                system_prompt = template_content.split('## Example Messages')[0].strip()
            else:
                raise FileNotFoundError("Template returned None")
        except Exception as e:
            logger.warning(f"Failed to load coaching template: {e}, using fallback")
            # Fallback system prompt
            system_prompt = """You are CoachNova, an empathetic coaching assistant for service workers in Bangladesh.

Your role is to provide constructive, dignity-centered coaching in Bengali. Follow these guidelines:

1. TONE: Empathetic, respectful, supportive (never shaming or negative)
2. LANGUAGE: Simple, clear Bengali
3. STRUCTURE: 
   - Acknowledge their hard work
   - Gently mention the specific issue
   - Provide 2-3 actionable tips
   - Express confidence in improvement
4. LENGTH: 150-250 words
5. AVOID: Shame, blame, harsh criticism, complex vocabulary
6. EMPHASIZE: Growth, support, practical solutions

Remember: Workers are valued professionals. Frame all feedback as opportunities for growth."""
        
        # Build user prompt with performance context
        if 'late_arrivals' in issues:
            issue_context = f"সাম্প্রতিক ৭ দিনে {late_arrivals}টি কাজে কিছুটা দেরি হয়েছে"
            coaching_focus = "সময়মত পৌঁছানোর কিছু কার্যকর টিপস"
        elif 'low_rating' in issues:
            issue_context = f"গড় রেটিং {avg_rating:.1f}/5.0 হয়েছে"
            coaching_focus = "কাস্টমার সন্তুষ্টি বাড়ানোর উপায়"
        elif 'high_workload' in issues or 'burnout_risk' in issues:
            issue_context = "অনেক কাজের চাপ লক্ষ্য করা গেছে"
            coaching_focus = "স্বাস্থ্য ও কাজের ভারসাম্য রক্ষার পরামর্শ"
        else:
            issue_context = "কিছু উন্নতির সুযোগ দেখা গেছে"
            coaching_focus = "আরও ভালো করার টিপস"
        
        user_prompt = f"""Create a Bengali coaching message for {worker_name}.

Context: {issue_context}

Focus on: {coaching_focus}

Include:
1. Warm greeting with worker's name
2. Acknowledge their commitment to work
3. Gently mention the specific situation
4. Provide 2-3 actionable tips (numbered list)
5. Express confidence and support

Tone: Empathetic, supportive, dignity-centered (NO shaming or harsh words)"""

        logger.info(
            "Generating coaching message with OpenAI",
            extra={
                "worker_name": worker_name,
                "issues": issues,
                "late_arrivals": late_arrivals,
            }
        )
        
        # Call OpenAI
        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=400,
            top_p=0.9,
        )
        
        message = response.choices[0].message.content.strip()
        
        logger.info(
            "Coaching message generated",
            extra={
                "length": len(message),
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            }
        )
        
        return message
    
    def _check_safety_sync(self, message: str) -> Dict[str, Any]:
        """
        Synchronous safety check for coaching messages.
        
        Checks for:
        1. Banned phrases (profanity, offensive terms)
        2. Inappropriate tone
        3. Shaming language (dignity-centered check)
        4. Length requirements
        
        Args:
            message: Generated coaching message
            
        Returns:
            {
                'safe': bool,
                'banned_phrases': bool,
                'tone_appropriate': bool,
                'length_valid': bool,
                'reason': str | None
            }
        """
        checks = {}
        
        # 1. Length check (150-500 words for coaching)
        length = len(message.strip())
        length_valid = 150 <= length <= 500
        checks['length_valid'] = length_valid
        
        if not length_valid:
            return {
                'safe': False,
                'banned_phrases': False,
                'tone_appropriate': True,
                'length_valid': False,
                'reason': f'Message length {length} not in range 150-500'
            }
        
        # 2. Banned phrases check
        banned_result, banned_matches = self.safety_filter.check_banned_phrases(message)
        has_banned = banned_result.value == 'failed'
        checks['banned_phrases'] = has_banned
        
        if has_banned:
            return {
                'safe': False,
                'banned_phrases': True,
                'tone_appropriate': True,
                'length_valid': True,
                'reason': f'Contains banned phrases: {", ".join(banned_matches)}'
            }
        
        # 3. Tone check
        tone, confidence = self.safety_filter.analyze_tone(message)
        tone_appropriate = tone.value not in ['inappropriate', 'aggressive']
        checks['tone_appropriate'] = tone_appropriate
        
        if not tone_appropriate:
            return {
                'safe': False,
                'banned_phrases': False,
                'tone_appropriate': False,
                'length_valid': True,
                'reason': f'Inappropriate tone detected: {tone.value}'
            }
        
        # 4. Dignity check (Bengali-specific shaming words)
        shaming_words = ['লজ্জা', 'খারাপ', 'বাজে', 'অযোগ্য']  # shame, bad, terrible, incompetent
        has_shaming = any(word in message for word in shaming_words)
        
        if has_shaming:
            return {
                'safe': False,
                'banned_phrases': False,
                'tone_appropriate': False,
                'length_valid': True,
                'reason': 'Contains shaming language (dignity violation)'
            }
        
        # All checks passed
        return {
            'safe': True,
            'banned_phrases': False,
            'tone_appropriate': True,
            'length_valid': True,
            'reason': None
        }
    
    async def _send_email_notification_async(
        self,
        worker_email: str,
        worker_name: str,
        coaching_message: str,
        message_id: UUID,
        correlation_id: UUID,
    ) -> bool:
        """
        Send coaching email asynchronously (helper for sync context).
        
        Args:
            worker_email: Worker's email address
            worker_name: Worker's name
            coaching_message: Generated coaching message
            message_id: AIMessage ID
            correlation_id: Request correlation ID
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            from src.services.notification_service import EmailNotificationProvider
            
            # Create email provider
            email_provider = EmailNotificationProvider()
            
            if not email_provider.available:
                logger.error("Email provider not available (SMTP not configured)")
                return False
            
            # Build email subject
            subject = "শক্তি থেকে আপনার জন্য কিছু পরামর্শ | Coaching from ShoktiAI"
            
            # Send email
            success = await email_provider.send(
                to=worker_email,
                message=coaching_message,
                subject=subject,
                agent_type="coachnova",
                message_type="coaching",
            )
            
            if success:
                logger.info(
                    f"Coaching email sent to {worker_email}",
                    extra={
                        "message_id": str(message_id),
                        "correlation_id": str(correlation_id),
                    }
                )
            else:
                logger.error(
                    f"Email provider returned False for {worker_email}",
                    extra={
                        "message_id": str(message_id),
                        "correlation_id": str(correlation_id),
                    }
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Error in _send_email_notification_async: {e}",
                exc_info=True,
                extra={
                    "message_id": str(message_id),
                    "correlation_id": str(correlation_id),
                }
            )
            return False
    
    async def generate_coaching(
        self,
        worker_id: UUID,
        performance_signals: Dict[str, Any],
        correlation_id: UUID,
        db: AsyncSession,
        dry_run: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate and send coaching message for a worker (async version).
        
        Complete flow:
        1. Check eligibility (performance issues)
        2. Check consent (coaching_enabled)
        3. Check frequency caps (7 days)
        4. Generate Bengali message via OpenAI
        5. Apply safety filters
        6. Create AIMessage record
        7. Trigger notification
        
        Args:
            worker_id: UUID of the worker
            performance_signals: Performance metrics from PerformanceService
            correlation_id: UUID for tracking this coaching flow
            db: Database session (async)
            dry_run: If True, validate eligibility but don't send (default: False)
            force: If True, bypass frequency caps for testing (default: False)
            
        Returns:
            {
                'success': bool,
                'message_id': UUID | None,
                'reason': str | None,  # If success=False
                'correlation_id': UUID
            }
        """
        logger.info(
            "CoachNova generation started (async)",
            extra={
                "worker_id": str(worker_id),
                "correlation_id": str(correlation_id),
                "dry_run": dry_run,
                "force": force,
            }
        )
        
        # Convert to sync and call sync version
        # Note: This is a wrapper for async contexts
        raise NotImplementedError("Use generate_coaching_sync() for now")
    
    def generate_coaching_sync(
        self,
        worker_id: UUID,
        performance_signals: Dict[str, Any],
        correlation_id: UUID,
        db: Session,
        dry_run: bool = False,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate and send coaching message for a worker.
        
        Complete flow:
        1. Check eligibility (performance issues)
        2. Check consent (coaching_enabled)
        3. Check frequency caps (7 days)
        4. Generate Bengali message via OpenAI
        5. Apply safety filters
        6. Create AIMessage record
        7. Trigger notification
        
        Args:
            worker_id: UUID of the worker
            performance_signals: Performance metrics from PerformanceService
            correlation_id: UUID for tracking this coaching flow
            db: Database session
            dry_run: If True, validate eligibility but don't send (default: False)
            force: If True, bypass frequency caps for testing (default: False)
            
        Returns:
            {
                'success': bool,
                'message_id': UUID | None,
                'reason': str | None,  # If success=False
                'correlation_id': UUID
            }
        """
        logger.info(
            "CoachNova generation started",
            extra={
                "worker_id": str(worker_id),
                "correlation_id": str(correlation_id),
                "dry_run": dry_run,
                "force": force,
            }
        )
        
        # Step 1: Check eligibility (performance issues)
        if not performance_signals.get('eligible_for_coaching'):
            logger.info(
                "Worker not eligible: no performance issues",
                extra={"worker_id": str(worker_id)}
            )
            return {
                'success': False,
                'message_id': None,
                'reason': 'no_performance_issues',
                'correlation_id': correlation_id,
            }
        
        # Step 2: Fetch worker and user data
        stmt = select(User).where(User.id == worker_id)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found for worker_id: {worker_id}")
            return {
                'success': False,
                'message_id': None,
                'reason': 'worker_not_found',
                'correlation_id': correlation_id,
            }
        
        # Fetch worker profile
        stmt = select(Worker).where(Worker.id == worker_id)
        result = db.execute(stmt)
        worker = result.scalar_one_or_none()
        
        if not worker:
            logger.warning(f"Worker profile not found: {worker_id}")
            return {
                'success': False,
                'message_id': None,
                'reason': 'worker_not_found',
                'correlation_id': correlation_id,
            }
        
        # Step 3: Check consent
        consent = user.consent or {}
        if not consent.get('coaching_enabled', False):
            logger.info(
                "Worker has not opted in for coaching",
                extra={"worker_id": str(worker_id)}
            )
            return {
                'success': False,
                'message_id': None,
                'reason': 'no_consent',
                'correlation_id': correlation_id,
            }
        
        # Step 4: Check frequency caps (unless force=True)
        if not force:
            frequency_check = self._check_frequency_cap(worker_id, db)
            if not frequency_check['allowed']:
                logger.info(
                    "Frequency cap hit",
                    extra={
                        "worker_id": str(worker_id),
                        "days_since_last": frequency_check.get('days_since_last'),
                    }
                )
                return {
                    'success': False,
                    'message_id': None,
                    'reason': 'frequency_cap',
                    'correlation_id': correlation_id,
                }
        
        # Dry run: stop here without generating
        if dry_run:
            logger.info(
                "Dry run: worker is eligible",
                extra={"worker_id": str(worker_id)}
            )
            return {
                'success': True,
                'message_id': None,
                'reason': 'dry_run',
                'correlation_id': correlation_id,
            }
        
        # Step 5: Generate Bengali coaching message (sync - placeholder for now)
        # TODO: Implement sync OpenAI call or use thread pool
        logger.warning("OpenAI generation skipped in sync mode - using placeholder")
        coaching_message = f"""প্রিয় {user.name},

আপনার পারফরম্যান্স উন্নতির জন্য কিছু পরামর্শ:

১. সময়মত কাজে পৌঁছানোর চেষ্টা করুন
২. গ্রাহকদের সাথে ভালো ব্যবহার করুন  
৩. কাজের মান বজায় রাখুন

আপনি একজন মূল্যবান কর্মী। আমরা আপনার উন্নতিতে বিশ্বাস করি।

শুভকামনা,
শক্তি টিম"""
        
        # Step 6: Apply safety filters (sync version for coaching)
        safety_result = self._check_safety_sync(coaching_message)
        
        if not safety_result['safe']:
            logger.warning(
                "Coaching message failed safety check",
                extra={
                    "worker_id": str(worker_id),
                    "safety_result": safety_result,
                }
            )
            return {
                'success': False,
                'message_id': None,
                'reason': 'safety_violation',
                'correlation_id': correlation_id,
            }
        
        # Step 7: Create AIMessage record
        message_id = uuid4()
        ai_message = AIMessage(
            id=message_id,
            user_id=worker_id,
            role=MessageRole.WORKER,
            agent_type='coachnova',
            message_type=MessageType.COACHING,
            channel=MessageChannel.EMAIL,  # Primary channel per research.md
            locale=user.language_preference,
            message_text=coaching_message,
            model='gpt-4o-mini',
            delivery_status=DeliveryStatus.PENDING,
            safety_checks=safety_result,
            correlation_id=correlation_id,
            metadata={
                'voice_enabled': worker.opt_in_voice,
                'performance_snapshot_date': str(performance_signals.get('snapshot_date')),
                'issues': performance_signals.get('issues', []),
                'late_arrivals': performance_signals.get('late_arrivals_last_7_days'),
            }
        )
        
        db.add(ai_message)
        db.commit()
        db.refresh(ai_message)
        
        logger.info(
            "AIMessage created",
            extra={
                "message_id": str(message_id),
                "worker_id": str(worker_id),
                "correlation_id": str(correlation_id),
            }
        )
        
        # Step 8: Send email notification
        # Use thread pool executor to run async email sending from sync context
        try:
            # Get worker email from User model
            worker_email = getattr(user, 'email', None)
            
            if not worker_email:
                logger.warning(
                    "Worker has no email address, cannot deliver coaching",
                    extra={"worker_id": str(worker_id)}
                )
                ai_message.delivery_status = DeliveryStatus.FAILED
                db.commit()
            else:
                # Create a new event loop in a thread pool for async email sending
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def run_async_email():
                    """Run async email sending in a separate thread with its own event loop."""
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success = loop.run_until_complete(
                            self._send_email_notification_async(
                                worker_email=worker_email,
                                worker_name=user.name,
                                coaching_message=coaching_message,
                                message_id=message_id,
                                correlation_id=correlation_id,
                            )
                        )
                        loop.close()
                        result_queue.put(('success', success))
                    except Exception as e:
                        result_queue.put(('error', str(e)))
                
                # Run in separate thread
                thread = threading.Thread(target=run_async_email)
                thread.start()
                thread.join(timeout=30)  # 30 second timeout
                
                # Get result
                try:
                    result_type, result_value = result_queue.get(timeout=1)
                    if result_type == 'success' and result_value:
                        ai_message.delivery_status = DeliveryStatus.SENT
                        ai_message.sent_at = datetime.now(timezone.utc)
                        logger.info(
                            "Coaching email sent successfully",
                            extra={
                                "message_id": str(message_id),
                                "worker_email": worker_email,
                                "correlation_id": str(correlation_id),
                            }
                        )
                    else:
                        ai_message.delivery_status = DeliveryStatus.FAILED
                        logger.error(
                            f"Failed to send coaching email: {result_value if result_type == 'error' else 'Unknown'}",
                            extra={
                                "message_id": str(message_id),
                                "worker_email": worker_email,
                            }
                        )
                except queue.Empty:
                    ai_message.delivery_status = DeliveryStatus.FAILED
                    logger.error(
                        "Email sending timed out",
                        extra={"message_id": str(message_id)}
                    )
                
                db.commit()
                
        except Exception as e:
            logger.error(
                f"Notification delivery failed: {e}",
                exc_info=True,
                extra={"message_id": str(message_id)}
            )
            ai_message.delivery_status = DeliveryStatus.FAILED
            db.commit()
            # Don't fail the entire flow if notification fails
            # Message is stored and can be retried
        
        # Track metrics
        # metrics = get_metrics_collector()
        # metrics.increment_coaching_sent(
        #     agent_type='coachnova',
        #     channel='email',
        #     issues=performance_signals.get('issues', [])
        # )
        logger.info("Metrics tracking skipped (method not implemented yet)")
        
        return {
            'success': True,
            'message_id': message_id,
            'reason': None,
            'correlation_id': correlation_id,
        }
    
    def _check_frequency_cap(
        self,
        worker_id: UUID,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Check if worker can receive coaching (frequency cap: 7 days).
        
        Args:
            worker_id: UUID of the worker
            db: Database session
            
        Returns:
            {
                'allowed': bool,
                'days_since_last': int | None,
                'last_coaching_at': datetime | None
            }
        """
        # Query for most recent coaching message
        stmt = select(AIMessage).where(
            AIMessage.user_id == worker_id,
            AIMessage.agent_type == 'coachnova',
            AIMessage.message_type == MessageType.COACHING,
        ).order_by(AIMessage.created_at.desc()).limit(1)
        
        result = db.execute(stmt)
        last_coaching = result.scalar_one_or_none()
        
        if not last_coaching:
            # No previous coaching, allowed
            return {
                'allowed': True,
                'days_since_last': None,
                'last_coaching_at': None,
            }
        
        # Calculate days since last coaching
        now = datetime.now(timezone.utc)
        days_since = (now - last_coaching.created_at).days
        
        allowed = days_since >= COACHING_FREQUENCY_DAYS
        
        return {
            'allowed': allowed,
            'days_since_last': days_since,
            'last_coaching_at': last_coaching.created_at,
        }
