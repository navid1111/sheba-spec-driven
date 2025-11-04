"""
SmartEngage Orchestrator - AI-Powered Customer Reminder System.

This module orchestrates the complete SmartEngage flow:
1. Segment eligible customers (via SegmentationService)
2. Generate personalized Bengali reminder messages (via OpenAI)
3. Apply safety filters (banned phrases, tone, content moderation)
4. Generate deep links with promo codes (via DeepLinkGenerator)
5. Send notifications (via EmailNotificationProvider)
6. Track outcomes in database (AIMessage records)

The orchestrator respects:
- Marketing consent
- Frequency caps (24h between messages)
- Send windows (9am-6pm local time)
- Safety guardrails (reject inappropriate content)
"""
import asyncio
from typing import Optional, Dict, List, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.lib.logging import get_logger
from src.lib.db import get_db
from src.lib.deeplink import get_deep_link_generator, DeepLinkGenerator
from src.services.segmentation_service import SegmentationService
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
from src.models.customers import Customer
from src.models.services import Service
from src.models.bookings import Booking

logger = get_logger(__name__)


class SmartEngageOrchestrator:
    """
    SmartEngage orchestrator for AI-powered customer reminders.
    
    Coordinates segmentation, message generation, safety filtering,
    and notification delivery for personalized booking reminders.
    """
    
    def __init__(
        self,
        db_session: Session,
        openai_client: Optional[OpenAIClient] = None,
        safety_filter: Optional[SafetyFilter] = None,
        deeplink_generator: Optional[DeepLinkGenerator] = None,
        notification_service: Optional[NotificationService] = None,
        segmentation_service: Optional[SegmentationService] = None,
    ):
        """
        Initialize SmartEngage orchestrator.
        
        Args:
            db_session: Database session for queries and persistence
            openai_client: OpenAI client (defaults to global instance)
            safety_filter: Safety filter (defaults to global instance)
            deeplink_generator: Deep link generator (defaults to global instance)
            notification_service: Notification service (defaults to global instance)
            segmentation_service: Segmentation service (created if not provided)
        """
        self.db = db_session
        self.openai_client = openai_client or get_openai_client()
        self.safety_filter = safety_filter or get_safety_filter(use_openai_moderation=False)
        self.deeplink_generator = deeplink_generator or get_deep_link_generator()
        self.notification_service = notification_service or get_notification_service(db_session)
        self.segmentation_service = segmentation_service or SegmentationService(db_session)
        
        logger.info("SmartEngageOrchestrator initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _generate_message_with_openai(
        self,
        customer: Customer,
        service: Service,
        last_booking: Booking,
        promo_code: Optional[str] = None,
    ) -> str:
        """
        Generate personalized Bengali reminder message using OpenAI.
        
        Retries up to 3 times with exponential backoff on failures.
        
        Args:
            customer: Customer to generate message for
            service: Service they previously booked
            last_booking: Their last booking record
            promo_code: Optional promo code to include
            
        Returns:
            Generated message text in Bengali
            
        Raises:
            Exception: If OpenAI call fails after retries
        """
        if not self.openai_client.is_available():
            raise ValueError("OpenAI client not configured")
        
        # Calculate days since last booking
        days_since = (datetime.now(timezone.utc) - last_booking.finished_at).days
        
        # Build context for OpenAI
        context = {
            "customer_name": customer.name if hasattr(customer, "name") else "মূল্যবান গ্রাহক",
            "service_name": service.name,
            "service_name_bn": getattr(service, "name_bn", service.name),
            "days_since": days_since,
            "promo_code": promo_code,
            "has_promo": bool(promo_code),
        }
        
        # Construct prompt
        prompt = self._build_reminder_prompt(context)
        
        # Call OpenAI
        logger.info(f"Generating message for customer with OpenAI (service: {service.name})")
        
        client = self.openai_client.get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant for Sheba.xyz, a Bangladeshi home services platform. "
                        "Generate friendly, professional Bengali reminder messages for customers. "
                        "Keep messages concise (2-3 sentences), warm, and action-oriented. "
                        "Use Bengali script (not transliteration). "
                        "Always include a clear call-to-action about booking."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )
        
        message_text = response.choices[0].message.content.strip()
        
        logger.info(f"Generated message (length: {len(message_text)})")
        return message_text
    
    def _build_reminder_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build prompt for OpenAI message generation.
        
        Args:
            context: Dictionary with customer/service context
            
        Returns:
            Prompt string
        """
        promo_section = ""
        if context["has_promo"]:
            promo_section = f"\n- মেনশন করুন প্রোমো কোড: {context['promo_code']}"
        
        prompt = f"""
একটি বন্ধুত্বপূর্ণ রিমাইন্ডার মেসেজ লিখুন বাংলায়:

গ্রাহক: {context['customer_name']}
সার্ভিস: {context['service_name_bn']}
শেষ বুকিং: {context['days_since']} দিন আগে

নির্দেশনা:
- উষ্ণ এবং ব্যক্তিগত টোন ব্যবহার করুন
- 2-3 বাক্যে সংক্ষিপ্ত রাখুন
- স্পষ্ট কল-টু-অ্যাকশন দিন (আবার বুক করুন){promo_section}
- শুধু মেসেজ টেক্সট লিখুন (no labels, no "Message:" prefix)

উদাহরণ স্টাইল:
"আপনার {context['service_name_bn']} সার্ভিসের সময় হয়ে গেছে! আবার বুক করে আপনার ঘর ঝকঝকে করুন। এখনই অ্যাপে গিয়ে বুক করুন।"
"""
        return prompt.strip()
    
    async def _apply_safety_filter(
        self,
        message_text: str,
        correlation_id: UUID,
    ) -> Dict[str, Any]:
        """
        Apply safety checks to generated message.
        
        Args:
            message_text: Generated message text
            correlation_id: Correlation ID for logging
            
        Returns:
            Safety check results dictionary
        """
        logger.info(f"Applying safety filter (correlation_id: {correlation_id})")
        
        safety_result = await self.safety_filter.check_message(
            message_text,
            min_length=10,
            max_length=500,
        )
        
        if not safety_result["safe"]:
            logger.warning(
                f"Safety filter rejected message (correlation_id: {correlation_id}): "
                f"{safety_result.get('reason')}"
            )
        
        return safety_result
    
    async def generate_and_send_reminder(
        self,
        customer_id: UUID,
        correlation_id: Optional[UUID] = None,
        promo_code: Optional[str] = None,
        ttl_hours: int = 48,
    ) -> Dict[str, Any]:
        """
        Generate and send a personalized reminder for a customer.
        
        This is the main entry point for SmartEngage. It:
        1. Fetches customer data and booking history
        2. Generates personalized message via OpenAI
        3. Applies safety filters
        4. Generates deep link with promo code
        5. Sends email notification
        6. Creates AIMessage record
        
        Args:
            customer_id: Customer to send reminder to
            correlation_id: Optional correlation ID for tracking
            promo_code: Optional promo code to include
            ttl_hours: Deep link expiration time (default 48h)
            
        Returns:
            Dictionary with results:
            {
                "success": bool,
                "message_id": UUID (if successful),
                "reason": str (if failed),
                "correlation_id": UUID,
            }
        """
        correlation_id = correlation_id or uuid4()
        
        logger.info(
            f"Starting SmartEngage reminder generation "
            f"(customer_id: {customer_id}, correlation_id: {correlation_id})"
        )
        
        try:
            # 1. Fetch customer and booking history
            customer = self.db.get(Customer, customer_id)
            if not customer:
                return {
                    "success": False,
                    "reason": "Customer not found",
                    "correlation_id": correlation_id,
                }
            
            # Get customer's user record for email/language
            from src.models.users import User
            user = self.db.get(User, customer.id)  # Customer.id == User.id
            if not user:
                return {
                    "success": False,
                    "reason": "User record not found",
                    "correlation_id": correlation_id,
                }
            
            # Check marketing consent
            if not user.consent.get("marketing_consent"):
                logger.info(f"Customer {customer_id} has not consented to marketing")
                return {
                    "success": False,
                    "reason": "No marketing consent",
                    "correlation_id": correlation_id,
                }
            
            # Get last booking
            last_booking = self.segmentation_service.get_last_booking(customer)
            if not last_booking:
                return {
                    "success": False,
                    "reason": "No booking history",
                    "correlation_id": correlation_id,
                }
            
            # Get service
            service = self.db.get(Service, last_booking.service_id)
            if not service:
                return {
                    "success": False,
                    "reason": "Service not found",
                    "correlation_id": correlation_id,
                }
            
            # 2. Generate message with OpenAI
            try:
                message_text = await self._generate_message_with_openai(
                    customer, service, last_booking, promo_code
                )
            except Exception as e:
                logger.error(
                    f"OpenAI message generation failed (correlation_id: {correlation_id}): {e}",
                    exc_info=True,
                )
                # Use fallback message
                message_text = self.safety_filter.get_fallback_message(
                    message_type="reminder",
                    locale=user.language_preference or "bn",
                )
            
            # 3. Apply safety filter
            safety_result = await self._apply_safety_filter(message_text, correlation_id)
            
            if not safety_result["safe"]:
                # Use fallback message
                logger.warning(f"Using fallback message due to safety rejection")
                message_text = self.safety_filter.get_fallback_message(
                    message_type="reminder",
                    locale=user.language_preference or "bn",
                )
                # Re-check fallback (should always pass)
                safety_result = await self._apply_safety_filter(message_text, correlation_id)
            
            # 4. Generate deep link
            deep_link = self.deeplink_generator.generate_booking_link(
                customer_id=customer_id,
                service_id=service.id,
                promo_code=promo_code,
                ttl_hours=ttl_hours,
                utm_campaign="smartengage_reminder",
                metadata={
                    "correlation_id": str(correlation_id),
                    "agent": "smartengage",
                },
            )
            
            # 5. Create AIMessage record (before sending for tracking)
            ai_message = AIMessage(
                id=uuid4(),
                user_id=user.id,
                role=MessageRole.CUSTOMER,
                agent_type="smartengage",
                channel=MessageChannel.EMAIL,
                message_type=MessageType.REMINDER,
                message_text=message_text,
                locale=user.language_preference or "bn",
                delivery_status=DeliveryStatus.PENDING,
                model="gpt-4o-mini",
                prompt_version=1,
                safety_checks=safety_result["checks"],
                metadata={
                    "service_id": str(service.id),
                    "service_name": service.name,
                    "promo_code": promo_code,
                    "deep_link": deep_link,
                    "ttl_hours": ttl_hours,
                },
                correlation_id=correlation_id,
            )
            self.db.add(ai_message)
            self.db.commit()
            self.db.refresh(ai_message)
            
            # 6. Send email notification
            try:
                # Build HTML email with deep link
                email_body = self._build_email_html(
                    message_text=message_text,
                    deep_link=deep_link,
                    customer_name=user.name,
                    service_name=getattr(service, "name_bn", service.name),
                    promo_code=promo_code,
                )
                
                # Get email provider and send
                email_provider = self.notification_service._get_provider(MessageChannel.EMAIL)
                if email_provider:
                    await email_provider.send(
                        to=user.email,
                        message=email_body,
                        subject=f"আপনার {getattr(service, 'name_bn', service.name)} সার্ভিসের রিমাইন্ডার",
                        agent_type="smartengage",
                        message_type="reminder",
                    )
                else:
                    raise ValueError("Email provider not available")
                
                # Update delivery status
                ai_message.delivery_status = DeliveryStatus.SENT
                ai_message.sent_at = datetime.now(timezone.utc)
                self.db.commit()
                
                logger.info(
                    f"SmartEngage reminder sent successfully "
                    f"(message_id: {ai_message.id}, correlation_id: {correlation_id})"
                )
                
                return {
                    "success": True,
                    "message_id": ai_message.id,
                    "correlation_id": correlation_id,
                }
            
            except Exception as e:
                logger.error(
                    f"Notification sending failed (correlation_id: {correlation_id}): {e}",
                    exc_info=True,
                )
                # Update delivery status to failed
                ai_message.delivery_status = DeliveryStatus.FAILED
                ai_message.error_message = str(e)
                self.db.commit()
                
                return {
                    "success": False,
                    "reason": f"Notification failed: {str(e)}",
                    "message_id": ai_message.id,
                    "correlation_id": correlation_id,
                }
        
        except Exception as e:
            logger.error(
                f"SmartEngage orchestration failed (correlation_id: {correlation_id}): {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "reason": f"Orchestration error: {str(e)}",
                "correlation_id": correlation_id,
            }
    
    def _build_email_html(
        self,
        message_text: str,
        deep_link: str,
        customer_name: str,
        service_name: str,
        promo_code: Optional[str] = None,
    ) -> str:
        """
        Build HTML email with Bengali message and deep link.
        
        Args:
            message_text: AI-generated message text
            deep_link: Booking deep link URL
            customer_name: Customer's name
            service_name: Service name in Bengali
            promo_code: Optional promo code
            
        Returns:
            HTML email body
        """
        promo_section = ""
        if promo_code:
            promo_section = f"""
            <div style="background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin: 16px 0;">
                <strong style="color: #1e40af;">প্রোমো কোড:</strong> 
                <code style="background: white; padding: 4px 8px; border-radius: 4px; font-size: 16px; font-weight: bold;">{promo_code}</code>
            </div>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sheba.xyz Reminder</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">Sheba.xyz</h1>
        <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 14px;">আপনার সেবায় নিয়োজিত</p>
    </div>
    
    <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        <p style="font-size: 16px; margin-bottom: 20px;">হাই {customer_name},</p>
        
        <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="font-size: 16px; line-height: 1.8; margin: 0;">
                {message_text}
            </p>
        </div>
        
        {promo_section}
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{deep_link}" 
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                এখনই বুক করুন
            </a>
        </div>
        
        <p style="font-size: 14px; color: #6b7280; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            এই লিংকটি পরবর্তী ৪৮ ঘন্টার জন্য বৈধ।
        </p>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #e5e7eb; text-align: center;">
            <p style="font-size: 12px; color: #9ca3af; margin: 5px 0;">
                Sheba.xyz - Bangladesh's Leading Home Services Platform
            </p>
            <p style="font-size: 12px; color: #9ca3af; margin: 5px 0;">
                আপনি যদি আর এই ধরনের রিমাইন্ডার পেতে না চান, 
                <a href="#" style="color: #667eea;">এখানে ক্লিক করুন</a>
            </p>
        </div>
    </div>
</body>
</html>
        """
        return html.strip()
    
    async def generate_and_send_bulk_reminders(
        self,
        booking_cadence_days: int = 21,
        send_window_start: int = 9,
        send_window_end: int = 18,
        batch_size: int = 50,
        promo_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate and send reminders to all eligible customers in bulk.
        
        This method:
        1. Finds eligible customers via segmentation
        2. Processes in batches to avoid overwhelming the system
        3. Respects frequency caps and consent
        4. Returns summary of results
        
        Args:
            booking_cadence_days: Days since last booking (default 21)
            send_window_start: Hour to start sending (9am local)
            send_window_end: Hour to stop sending (6pm local)
            batch_size: Number of customers to process per batch
            promo_code: Optional promo code for all customers
            
        Returns:
            Dictionary with summary:
            {
                "total_eligible": int,
                "sent": int,
                "failed": int,
                "skipped": int,
                "results": List[Dict],
            }
        """
        logger.info(
            f"Starting bulk SmartEngage campaign "
            f"(cadence: {booking_cadence_days} days, window: {send_window_start}-{send_window_end})"
        )
        
        # Convert hour integers to time strings for segmentation service
        send_window_start_str = f"{send_window_start:02d}:00"
        send_window_end_str = f"{send_window_end:02d}:00"
        
        # Find eligible customers
        eligible_customers = self.segmentation_service.identify_eligible_customers(
            booking_cadence_days=booking_cadence_days,
            send_window_start=send_window_start_str,
            send_window_end=send_window_end_str,
        )
        
        total_eligible = len(eligible_customers)
        logger.info(f"Found {total_eligible} eligible customers")
        
        # Process in batches
        results = []
        sent = 0
        failed = 0
        skipped = 0
        
        for i in range(0, total_eligible, batch_size):
            batch = eligible_customers[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} customers)")
            
            # Process batch concurrently
            # Note: eligible_customers is a list of UUIDs, not customer objects
            batch_tasks = [
                self.generate_and_send_reminder(
                    customer_id=customer_id,
                    promo_code=promo_code,
                )
                for customer_id in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count results
            for result in batch_results:
                if isinstance(result, Exception):
                    failed += 1
                    results.append({"success": False, "reason": str(result)})
                elif result["success"]:
                    sent += 1
                    results.append(result)
                else:
                    skipped += 1
                    results.append(result)
        
        logger.info(
            f"Bulk campaign complete: {sent} sent, {failed} failed, {skipped} skipped "
            f"(total eligible: {total_eligible})"
        )
        
        return {
            "total_eligible": total_eligible,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "results": results,
        }


def get_smartengage_orchestrator(db_session: Session) -> SmartEngageOrchestrator:
    """
    Factory function to create SmartEngage orchestrator.
    
    Args:
        db_session: Database session
        
    Returns:
        Configured SmartEngageOrchestrator instance
    """
    return SmartEngageOrchestrator(db_session)
