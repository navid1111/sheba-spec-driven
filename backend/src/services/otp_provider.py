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
        else:
            raise ValueError(
                f"Unknown OTP provider: {provider_name}. "
                f"Valid options: console, twilio"
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
