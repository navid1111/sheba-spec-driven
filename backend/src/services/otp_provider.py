"""OTP provider abstraction with console and Twilio adapters.

Provides pluggable OTP delivery for development (console) and production (Twilio).
OTP codes are generated, hashed, and stored with short TTL.
"""
import hashlib
import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.lib.settings import settings


class OTPProvider(ABC):
    """Abstract base class for OTP delivery providers."""
    
    @abstractmethod
    async def send_otp(self, phone: str, code: str) -> bool:
        """Send OTP code to phone number.
        
        Args:
            phone: Recipient phone number (E.164 format)
            code: OTP code to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass


class ConsoleOTPProvider(OTPProvider):
    """Console OTP provider for development/testing.
    
    Prints OTP codes to console instead of sending via SMS.
    Useful for local development without Twilio credentials.
    """
    
    async def send_otp(self, phone: str, code: str) -> bool:
        """Print OTP to console."""
        print(f"\n{'='*60}")
        print(f"📱 OTP for {phone}: {code}")
        print(f"{'='*60}\n")
        return True


class TwilioOTPProvider(OTPProvider):
    """Twilio SMS OTP provider for production.
    
    Sends OTP codes via Twilio SMS API.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER.
    """
    
    def __init__(self):
        """Initialize Twilio client."""
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise ValueError(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN environment variables."
            )
        
        try:
            from twilio.rest import Client
            self.client = Client(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
        except ImportError:
            raise ImportError(
                "Twilio library not installed. "
                "Install with: pip install twilio"
            )
    
    async def send_otp(self, phone: str, code: str) -> bool:
        """Send OTP via Twilio SMS."""
        try:
            message = self.client.messages.create(
                body=f"Your ShoktiAI verification code is: {code}",
                from_=settings.twilio_from_number,
                to=phone
            )
            return message.sid is not None
        except Exception as e:
            print(f"❌ Twilio SMS failed: {e}")
            return False


class MoceanOTPProvider(OTPProvider):
    """Mocean SMS OTP provider for Bangladesh.
    
    Sends OTP codes via Mocean SMS API (works in Bangladesh).
    Requires MOCEAN_TOKEN environment variable.
    """
    
    def __init__(self):
        """Initialize Mocean client."""
        if not settings.mocean_token:
            raise ValueError(
                "Mocean token not configured. "
                "Set MOCEAN_TOKEN environment variable."
            )
        
        try:
            from moceansdk import Client, Basic
            self.client = Client(Basic(api_token=settings.mocean_token))
        except ImportError:
            raise ImportError(
                "Mocean SDK not installed. "
                "Install with: pip install moceansdk"
            )
    
    async def send_otp(self, phone: str, code: str) -> bool:
        """Send OTP via Mocean SMS."""
        try:
            # Remove '+' from phone number if present (Mocean expects raw digits)
            clean_phone = phone.lstrip('+')
            
            res = self.client.sms.create({
                "mocean-from": settings.mocean_from,
                "mocean-to": clean_phone,
                "mocean-text": f"Your ShoktiAI verification code is: {code}"
            }).send()
            
            # Check if message was sent successfully
            # Status 0 means success in Mocean API
            if res and 'messages' in res:
                for msg in res['messages']:
                    if msg.get('status') == 0:
                        return True
            
            print(f"❌ Mocean SMS failed: {res}")
            return False
        except Exception as e:
            print(f"❌ Mocean SMS failed: {e}")
            return False


class EmailOTPProvider(OTPProvider):
    """Email OTP provider using SMTP.
    
    Sends OTP codes via email using Gmail SMTP or other SMTP servers.
    Requires SMTP configuration in environment variables.
    """
    
    def __init__(self):
        """Initialize SMTP configuration."""
        if not settings.smtp_username or not settings.smtp_password:
            raise ValueError(
                "SMTP credentials not configured. "
                "Set SMTP_USERNAME and SMTP_PASSWORD environment variables."
            )
        
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email or settings.smtp_username
        self.from_name = settings.smtp_from_name
    
    async def send_otp(self, email: str, code: str) -> bool:
        """Send OTP via email.
        
        Args:
            email: Recipient email address
            code: OTP code to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'Your ShoktiAI Verification Code: {code}'
            msg['From'] = f'{self.from_name} <{self.from_email}>'
            msg['To'] = email
            
            # Plain text version
            text = f"""
Hello,

Your ShoktiAI verification code is: {code}

This code will expire in 5 minutes.

If you didn't request this code, please ignore this email.

Best regards,
ShoktiAI Team
            """
            
            # HTML version
            html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
      <h2 style="color: #2563eb;">ShoktiAI Verification Code</h2>
      <p>Hello,</p>
      <p>Your verification code is:</p>
      <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
        <h1 style="color: #2563eb; font-size: 36px; letter-spacing: 8px; margin: 0;">{code}</h1>
      </div>
      <p>This code will expire in <strong>5 minutes</strong>.</p>
      <p style="color: #6b7280; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
      <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
      <p style="color: #6b7280; font-size: 12px;">Best regards,<br>ShoktiAI Team</p>
    </div>
  </body>
</html>
            """
            
            # Attach both versions
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email using SSL (port 465)
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
            
            print(f"✅ Email OTP sent to {email}")
            return True
            
        except Exception as e:
            print(f"❌ Email send failed: {e}")
            return False


class OTPService:
    """OTP service for generating, storing, and verifying codes.
    
    Handles OTP lifecycle:
    - Generate random 6-digit codes
    - Hash codes for secure storage
    - Track expiration (default 5 minutes)
    - Verify codes against stored hashes
    
    In-memory storage for MVP; migrate to Redis/DB for production.
    """
    
    def __init__(self):
        """Initialize OTP service with configured provider."""
        self.provider = self._get_provider()
        # In-memory storage: {phone: (hashed_code, expiry_time)}
        # TODO: Replace with Redis or database for production
        self._store: dict[str, tuple[str, datetime]] = {}
    
    def _get_provider(self) -> OTPProvider:
        """Get OTP provider based on configuration."""
        provider_name = settings.otp_provider.lower()
        
        if provider_name == "console":
            return ConsoleOTPProvider()
        elif provider_name == "twilio":
            try:
                return TwilioOTPProvider()
            except ImportError:
                # Fall back to console if Twilio not available
                print("⚠️  Twilio not available, falling back to console provider")
                return ConsoleOTPProvider()
        elif provider_name == "mocean":
            try:
                return MoceanOTPProvider()
            except ImportError:
                # Fall back to console if Mocean not available
                print("⚠️  Mocean SDK not available, falling back to console provider")
                return ConsoleOTPProvider()
        elif provider_name == "email":
            try:
                return EmailOTPProvider()
            except (ImportError, ValueError) as e:
                # Fall back to console if email not configured
                print(f"⚠️  Email provider not available ({e}), falling back to console provider")
                return ConsoleOTPProvider()
        else:
            raise ValueError(
                f"Unknown OTP provider: {provider_name}. "
                f"Valid options: console, twilio, mocean, email"
            )
    
    def generate_code(self) -> str:
        """Generate a random 6-digit OTP code."""
        return f"{secrets.randbelow(1000000):06d}"
    
    def _hash_code(self, code: str) -> str:
        """Hash OTP code for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()
    
    async def request_otp(self, phone: str) -> bool:
        """Generate and send OTP to phone number.
        
        Args:
            phone: Recipient phone number (E.164 format recommended)
            
        Returns:
            True if OTP sent successfully
            
        Raises:
            ValueError: If phone number is invalid
        """
        if not phone or len(phone) < 10:
            raise ValueError("Invalid phone number")
        
        # Generate code
        code = self.generate_code()
        
        # Calculate expiry
        expiry = datetime.now(timezone.utc) + timedelta(
            seconds=settings.otp_ttl_seconds
        )
        
        # Store hashed code
        hashed = self._hash_code(code)
        self._store[phone] = (hashed, expiry)
        
        # Send via provider
        success = await self.provider.send_otp(phone, code)
        
        if not success:
            # Clean up on failure
            del self._store[phone]
        
        return success
    
    async def verify_otp(self, phone: str, code: str) -> bool:
        """Verify OTP code for phone number.
        
        Args:
            phone: Phone number to verify
            code: OTP code to check
            
        Returns:
            True if code is valid and not expired
        """
        if phone not in self._store:
            return False
        
        hashed, expiry = self._store[phone]
        
        # Check expiration
        if datetime.now(timezone.utc) > expiry:
            # Clean up expired code
            del self._store[phone]
            return False
        
        # Verify hash
        if self._hash_code(code) != hashed:
            return False
        
        # Success - clean up used code
        del self._store[phone]
        return True
    
    def clear_otp(self, phone: str) -> None:
        """Clear OTP for phone number (e.g., on logout or rate limit)."""
        if phone in self._store:
            del self._store[phone]


# Global OTP service instance
otp_service = OTPService()
