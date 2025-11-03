"""Authentication service for OTP-based phone authentication.

Handles the complete authentication flow:
1. Request OTP: Generate and send code to phone
2. Verify OTP: Validate code and issue JWT token
3. User management: Create users on first login
"""
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.lib.jwt import create_access_token
from src.models.users import User
from src.services.otp_provider import otp_service


class AuthService:
    """Authentication service for OTP-based login.
    
    Provides phone-based authentication with OTP verification.
    Creates new users automatically on first login.
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize auth service with database session.
        
        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session
        self.otp_service = otp_service
    
    async def request_otp(self, phone: str) -> bool:
        """Request OTP code for phone number.
        
        Generates and sends OTP code via configured provider.
        Does not require user to exist - creates on verify if needed.
        
        Args:
            phone: Phone number in E.164 format (e.g., +8801712345678)
            
        Returns:
            True if OTP sent successfully
            
        Raises:
            ValueError: If phone number is invalid
            
        Example:
            >>> success = await auth_service.request_otp("+8801712345678")
        """
        # Validate phone format (basic check)
        if not phone or not phone.startswith("+"):
            raise ValueError("Phone must be in E.164 format (e.g., +8801712345678)")
        
        # Send OTP via provider
        success = await self.otp_service.request_otp(phone)
        return success
    
    async def verify_otp(
        self,
        phone: str,
        code: str,
        user_type: str = "CUSTOMER"
    ) -> Optional[dict]:
        """Verify OTP code and issue JWT token.
        
        Validates the OTP code for the phone number.
        If valid, creates user if they don't exist, then issues JWT.
        
        Args:
            phone: Phone number to verify
            code: OTP code to validate
            user_type: Type of user to create if new (CUSTOMER, WORKER, ADMIN)
            
        Returns:
            Dict with token and user info if successful, None if invalid code
            {
                "token": "jwt_token_string",
                "user_id": "uuid",
                "user_type": "CUSTOMER",
                "phone": "+8801712345678"
            }
            
        Example:
            >>> result = await auth_service.verify_otp("+8801712345678", "123456")
            >>> if result:
            ...     token = result["token"]
        """
        # Verify OTP code
        valid = await self.otp_service.verify_otp(phone, code)
        
        if not valid:
            return None
        
        # Get or create user
        user = await self._get_or_create_user(phone, user_type)
        
        # Generate JWT token
        # Handle both enum and string type values
        user_type_str = user.type.value if hasattr(user.type, 'value') else str(user.type)
        
        token = create_access_token(
            user_id=str(user.id),
            user_type=user_type_str
        )
        
        return {
            "token": token,
            "user_id": str(user.id),
            "user_type": user_type_str,
            "phone": user.phone
        }
    
    async def _get_or_create_user(
        self,
        phone: str,
        user_type: str
    ) -> User:
        """Get existing user or create new one.
        
        Args:
            phone: Phone number
            user_type: Type of user (CUSTOMER, WORKER, ADMIN)
            
        Returns:
            User object
        """
        # Try to find existing user
        stmt = select(User).where(User.phone == phone)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update last login time
            from datetime import datetime, timezone
            user.last_login_at = datetime.now(timezone.utc)
            await self.session.commit()
            return user
        
        # Create new user
        user = User(
            id=uuid4(),
            phone=phone,
            type=user_type,
            language_preference="bn",  # Bengali default for Bangladesh
            is_active=True,
            consent={
                "marketing": False,
                "notifications": True,
                "data_processing": True
            }
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    async def logout(self, phone: str) -> None:
        """Logout user by clearing their OTP.
        
        Optional cleanup operation.
        In production, might also blacklist JWT token.
        
        Args:
            phone: Phone number to logout
        """
        self.otp_service.clear_otp(phone)
