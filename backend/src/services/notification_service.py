"""
Notification service abstraction for sending messages via various channels.

All notifications are logged to the ai_messages table for tracking and analytics.
Supports multiple delivery channels: SMS (Twilio), Push (stub), WhatsApp (future), In-app (future).
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.logging import get_logger
from src.lib.settings import settings
from src.models.ai_messages import (
    AIMessage,
    MessageRole,
    MessageChannel,
    MessageType,
    DeliveryStatus,
)


logger = get_logger(__name__)


class NotificationProvider(ABC):
    """
    Abstract base class for notification delivery providers.
    """
    
    @abstractmethod
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Send notification via this provider.
        
        Args:
            to: Recipient identifier (phone number, device token, etc.)
            message: Message content to send
            **kwargs: Provider-specific parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @property
    @abstractmethod
    def channel(self) -> MessageChannel:
        """Return the channel this provider supports."""
        pass


class TwilioSMSProvider(NotificationProvider):
    """
    Twilio SMS provider for sending text messages.
    """
    
    def __init__(self):
        """Initialize Twilio client."""
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_from_number
        
        # Try to import Twilio
        try:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            self.available = True
            logger.info("Twilio SMS provider initialized")
        except ImportError:
            self.client = None
            self.available = False
            logger.warning("Twilio library not available, SMS will fail")
        except Exception as e:
            self.client = None
            self.available = False
            logger.error(f"Failed to initialize Twilio client: {e}")
    
    @property
    def channel(self) -> MessageChannel:
        """Return SMS channel."""
        return MessageChannel.SMS
    
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Send SMS via Twilio.
        
        Args:
            to: Phone number in E.164 format
            message: SMS text content
            **kwargs: Additional Twilio parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.available or not self.client:
            logger.error("Twilio client not available")
            return False
        
        try:
            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to,
                **kwargs
            )
            logger.info(f"SMS sent via Twilio: {msg.sid}", extra={"to": to})
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {e}", extra={"to": to})
            return False


class MoceanSMSProvider(NotificationProvider):
    """
    Mocean SMS provider for sending text messages (works in Bangladesh).
    """
    
    def __init__(self):
        """Initialize Mocean client."""
        self.api_token = settings.mocean_token
        self.from_name = settings.mocean_from
        
        # Try to import Mocean SDK
        try:
            from moceansdk import Client, Basic
            self.client = Client(Basic(api_token=self.api_token))
            self.available = True
            logger.info("Mocean SMS provider initialized")
        except ImportError:
            self.client = None
            self.available = False
            logger.warning("Mocean SDK not available, SMS will fail")
        except Exception as e:
            self.client = None
            self.available = False
            logger.error(f"Failed to initialize Mocean client: {e}")
    
    @property
    def channel(self) -> MessageChannel:
        """Return SMS channel."""
        return MessageChannel.SMS
    
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Send SMS via Mocean.
        
        Args:
            to: Phone number (will be cleaned of '+' prefix)
            message: SMS text content
            **kwargs: Additional Mocean parameters
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.available or not self.client:
            logger.error("Mocean client not available")
            return False
        
        try:
            # Remove '+' from phone number if present
            clean_phone = to.lstrip('+')
            
            res = self.client.sms.create({
                "mocean-from": self.from_name,
                "mocean-to": clean_phone,
                "mocean-text": message,
                **kwargs
            }).send()
            
            # Check if message was sent successfully (status 0)
            if res and 'messages' in res:
                for msg in res['messages']:
                    if msg.get('status') == 0:
                        msgid = msg.get('msgid', 'unknown')
                        logger.info(f"SMS sent via Mocean: {msgid}", extra={"to": to})
                        return True
            
            logger.error(f"Mocean API returned error: {res}", extra={"to": to})
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS via Mocean: {e}", extra={"to": to})
            return False


class ConsoleSMSProvider(NotificationProvider):
    """
    Console SMS provider for development/testing.
    Prints messages to console instead of sending.
    """
    
    @property
    def channel(self) -> MessageChannel:
        """Return SMS channel."""
        return MessageChannel.SMS
    
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Print SMS to console.
        
        Args:
            to: Phone number
            message: SMS text content
            **kwargs: Ignored
            
        Returns:
            Always True
        """
        print("\n" + "=" * 60)
        print(f"📱 SMS to {to}:")
        print(f"   {message}")
        print("=" * 60 + "\n")
        logger.info(f"SMS logged to console", extra={"to": to})
        return True


class PushNotificationProvider(NotificationProvider):
    """
    Push notification provider stub.
    TODO: Implement Firebase Cloud Messaging or similar.
    """
    
    @property
    def channel(self) -> MessageChannel:
        """Return push notification channel."""
        return MessageChannel.APP_PUSH
    
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Stub for push notifications.
        
        Args:
            to: Device token or user ID
            message: Notification content
            **kwargs: Notification parameters (title, data, etc.)
            
        Returns:
            True (stub always succeeds)
        """
        title = kwargs.get("title", "ShoktiAI")
        print("\n" + "=" * 60)
        print(f"🔔 Push Notification to {to}:")
        print(f"   Title: {title}")
        print(f"   Body: {message}")
        print("=" * 60 + "\n")
        logger.info(f"Push notification stub called", extra={"to": to})
        return True


class EmailNotificationProvider(NotificationProvider):
    """
    Email notification provider for AI messages.
    Sends rich HTML emails with AI-generated content.
    """
    
    def __init__(self):
        """Initialize SMTP configuration."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email or settings.smtp_username
        self.from_name = settings.smtp_from_name
        
        # Check if SMTP is configured
        if not self.smtp_username or not self.smtp_password:
            self.available = False
            logger.warning("SMTP not configured, email notifications will fail")
        else:
            self.available = True
            logger.info("Email notification provider initialized")
    
    @property
    def channel(self) -> MessageChannel:
        """Return EMAIL channel."""
        return MessageChannel.EMAIL
    
    async def send(
        self,
        to: str,
        message: str,
        **kwargs
    ) -> bool:
        """
        Send notification email.
        
        Args:
            to: Recipient email address
            message: Email content (can be plain text or HTML)
            **kwargs: Additional parameters:
                - subject: Email subject (default: "ShoktiAI Notification")
                - agent_type: AI agent type (smartengage, coachnova)
                - message_type: Message type (reminder, coaching, etc.)
                
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.available:
            logger.error("Email provider not available (SMTP not configured)")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Get optional parameters
            subject = kwargs.get("subject", "ShoktiAI Notification")
            agent_type = kwargs.get("agent_type", "ShoktiAI")
            message_type = kwargs.get("message_type", "notification")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = to
            
            # Plain text version (fallback)
            text_content = message
            
            # HTML version with styling
            html_content = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
      <h1 style="color: white; margin: 0; font-size: 28px;">ShoktiAI</h1>
      <p style="color: #e0e7ff; margin: 5px 0 0 0; font-size: 14px;">{agent_type.upper()} • {message_type.upper()}</p>
    </div>
    
    <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
      <div style="font-size: 16px; line-height: 1.8;">
        {message.replace(chr(10), '<br>')}
      </div>
      
      <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
        <p style="color: #6b7280; font-size: 12px; margin: 0;">
          This is an automated message from ShoktiAI. If you wish to unsubscribe, please contact support.
        </p>
      </div>
    </div>
    
    <div style="text-align: center; margin-top: 20px; color: #9ca3af; font-size: 12px;">
      <p>© 2025 ShoktiAI. All rights reserved.</p>
    </div>
  </body>
</html>
            """
            
            # Attach both versions
            part1 = MIMEText(text_content, 'plain')
            part2 = MIMEText(html_content, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email using SSL (port 465) or STARTTLS (port 587)
            if self.smtp_port == 465:
                # Use SMTP_SSL for port 465
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                # Use SMTP with STARTTLS for port 587
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            
            logger.info(f"Email notification sent to {to}", extra={"to": to, "subject": subject})
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}", extra={"to": to})
            return False


class NotificationService:
    """
    Main notification service that logs all sends to database.
    
    Handles:
    - Provider selection based on channel
    - Database logging to ai_messages table
    - Delivery status tracking
    - Correlation ID propagation
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize notification service.
        
        Args:
            db: Database session for logging messages
        """
        self.db = db
        
        # Initialize providers
        self._providers: dict[MessageChannel, NotificationProvider] = {}
        
        # SMS provider based on settings
        sms_provider_name = settings.otp_provider.lower()
        if sms_provider_name == "twilio" and settings.twilio_account_sid:
            self._providers[MessageChannel.SMS] = TwilioSMSProvider()
        elif sms_provider_name == "mocean" and settings.mocean_token:
            self._providers[MessageChannel.SMS] = MoceanSMSProvider()
        else:
            self._providers[MessageChannel.SMS] = ConsoleSMSProvider()
            logger.info("Using console SMS provider (dev mode)")
        
        # Email provider
        try:
            email_provider = EmailNotificationProvider()
            if email_provider.available:
                self._providers[MessageChannel.EMAIL] = email_provider
            else:
                logger.info("Email provider not available (SMTP not configured)")
        except Exception as e:
            logger.warning(f"Failed to initialize email provider: {e}")
        
        # Push notification stub
        self._providers[MessageChannel.APP_PUSH] = PushNotificationProvider()
        
        logger.info(f"NotificationService initialized with {len(self._providers)} providers")
    
    def _get_provider(self, channel: MessageChannel) -> Optional[NotificationProvider]:
        """
        Get provider for channel.
        
        Args:
            channel: Delivery channel
            
        Returns:
            Provider instance or None if not supported
        """
        return self._providers.get(channel)
    
    async def send_notification(
        self,
        to: str,
        message_text: str,
        channel: MessageChannel,
        agent_type: str,
        message_type: MessageType,
        role: MessageRole,
        user_id: Optional[UUID] = None,
        worker_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        locale: str = "bn",
        correlation_id: Optional[UUID] = None,
        model: Optional[str] = None,
        prompt_version: Optional[int] = None,
        safety_checks: Optional[dict] = None,
        **provider_kwargs
    ) -> Optional[UUID]:
        """
        Send notification and log to database.
        
        Args:
            to: Recipient identifier (phone, device token, etc.)
            message_text: Message content
            channel: Delivery channel (SMS, PUSH, etc.)
            agent_type: AI agent (smartengage, coachnova)
            message_type: Message purpose (reminder, coaching, etc.)
            role: Recipient role (customer, worker)
            user_id: Customer user ID (if role=customer)
            worker_id: Worker ID (if role=worker)
            template_id: Message template used
            locale: Language code
            correlation_id: Request correlation ID
            model: OpenAI model used
            prompt_version: Template version
            safety_checks: Safety filter results
            **provider_kwargs: Additional provider-specific parameters
            
        Returns:
            Message ID if created, None if failed
        """
        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = uuid4()
        
        # Create database record
        message = AIMessage(
            id=uuid4(),
            user_id=user_id,
            worker_id=worker_id,
            role=role,
            agent_type=agent_type,
            channel=channel,
            message_type=message_type,
            message_text=message_text,
            locale=locale,
            template_id=template_id,
            correlation_id=correlation_id,
            model=model,
            prompt_version=prompt_version,
            safety_checks=safety_checks,
            delivery_status=DeliveryStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        
        self.db.add(message)
        await self.db.flush()  # Get the ID without committing
        
        logger.info(
            f"Created message record",
            extra={
                "message_id": str(message.id),
                "correlation_id": str(correlation_id),
                "channel": channel.value,
                "agent": agent_type,
            }
        )
        
        # Get provider and send
        provider = self._get_provider(channel)
        if not provider:
            logger.error(f"No provider for channel: {channel.value}")
            message.delivery_status = DeliveryStatus.FAILED
            await self.db.commit()
            return message.id
        
        # Attempt delivery
        try:
            success = await provider.send(to, message_text, **provider_kwargs)
            
            if success:
                message.sent_at = datetime.now(timezone.utc)
                message.delivery_status = DeliveryStatus.SENT
                logger.info(
                    f"Message sent successfully",
                    extra={
                        "message_id": str(message.id),
                        "correlation_id": str(correlation_id),
                    }
                )
            else:
                message.delivery_status = DeliveryStatus.FAILED
                logger.warning(
                    f"Message send failed",
                    extra={
                        "message_id": str(message.id),
                        "correlation_id": str(correlation_id),
                    }
                )
        except Exception as e:
            logger.error(
                f"Error sending message: {e}",
                extra={
                    "message_id": str(message.id),
                    "correlation_id": str(correlation_id),
                },
                exc_info=True,
            )
            message.delivery_status = DeliveryStatus.FAILED
        
        # Commit changes
        await self.db.commit()
        
        return message.id
    
    async def update_delivery_status(
        self,
        message_id: UUID,
        status: DeliveryStatus
    ) -> bool:
        """
        Update message delivery status (e.g., from webhook).
        
        Args:
            message_id: Message ID
            status: New delivery status
            
        Returns:
            True if updated, False if not found
        """
        result = await self.db.execute(
            AIMessage.__table__.update()
            .where(AIMessage.id == message_id)
            .values(delivery_status=status, updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        
        if result.rowcount > 0:
            logger.info(f"Updated delivery status", extra={"message_id": str(message_id), "status": status.value})
            return True
        
        logger.warning(f"Message not found", extra={"message_id": str(message_id)})
        return False


# Factory function
def get_notification_service(db: AsyncSession) -> NotificationService:
    """
    Get NotificationService instance.
    
    Args:
        db: Database session
        
    Returns:
        NotificationService instance
    """
    return NotificationService(db)
