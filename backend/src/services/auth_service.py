"""Authentication service for OTP-based email authentication.

Handles the complete authentication flow:
1. Request OTP: Generate and send code to email
2. Verify OTP: Validate code and issue JWT token
3. User management: Create users on first login
"""
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from src.lib.jwt import create_access_token
from src.models.users import User, UserType
from src.services.otp_provider import otp_service


class AuthService:
    """Authentication service for OTP-based login.
    
    Provides email-based authentication with OTP verification.
    Creates new users automatically on first login.
    """
    
    def __init__(self, session: Session):
        """Initialize auth service with database session.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.otp_service = otp_service
    
    async def request_otp(self, email: str) -> bool:
        """Request OTP code for email.
        
        Generates and sends OTP code via configured provider.
        Does not require user to exist - creates on verify if needed.
        
        Args:
            email: Email address
            
        Returns:
            True if OTP sent successfully
            
        Raises:
            ValueError: If email is invalid
            
        Example:
            >>> success = await auth_service.request_otp("user@example.com")
        """
        # Validate email format (basic check)
        if not email or "@" not in email:
            raise ValueError("Invalid email address")
        
        if "." not in email.split("@")[1]:
            raise ValueError("Invalid email domain")
        
        # Send OTP via provider
        success = await self.otp_service.request_otp(email)
        return success
    
    async def verify_otp(
        self,
        email: str,
        code: str,
        user_type: str = "CUSTOMER"
    ) -> Optional[dict]:
        """Verify OTP code and issue JWT token.
        
        Validates the OTP code for the email.
        If valid, creates user if they don't exist, then issues JWT.
        
        Args:
            email: Email to verify
            code: OTP code to validate
            user_type: Type of user to create if new (CUSTOMER, WORKER, ADMIN)
            
        Returns:
            Dict with token and user info if successful, None if invalid code
            {
                "token": "jwt_token_string",
                "user_id": "uuid",
                "user_type": "CUSTOMER",
                "phone": None,
                "email": "user@example.com"
            }
            
        Example:
            >>> result = await auth_service.verify_otp("user@example.com", "123456")
            >>> if result:
            ...     token = result["token"]
        """
        # Verify OTP code
        valid = await self.otp_service.verify_otp(email, code)
        
        if not valid:
            return None
        
        # Get or create user (sync operation)
        user = self._get_or_create_user(email, user_type)
        
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
            "phone": user.phone,
            "email": user.email
        }
    
    def _get_or_create_user(
        self,
        email: str,
        user_type: str
    ) -> User:
        """Get existing user or create new one.
        
        Args:
            email: Email address
            user_type: Type of user (CUSTOMER, WORKER, ADMIN)
            
        Returns:
            User object
        """
        # Try to find existing user by email
        stmt = select(User).where(User.email == email)
        result = self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Update last login time
            from datetime import datetime, timezone
            user.last_login_at = datetime.now(timezone.utc)
            self.session.commit()
            return user
        
        # Create new user
        # Convert string user_type to enum (e.g., "CUSTOMER" -> UserType.CUSTOMER)
        if isinstance(user_type, str):
            user_type_enum = UserType[user_type.upper()] if hasattr(UserType, user_type.upper()) else UserType.CUSTOMER
        else:
            user_type_enum = user_type
            
        user = User(
            id=uuid4(),
            email=email,
            name=email.split("@")[0],  # Use email prefix as name
            type=user_type_enum,
            language_preference="bn",  # Bengali default for Bangladesh
            is_active=True,
            consent={
                "marketing": False,
                "notifications": True,
                "data_processing": True
            }
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    async def logout(self, phone: str) -> None:
        """Logout user by clearing their OTP.
        
        Optional cleanup operation.
        In production, might also blacklist JWT token.
        
        Args:
            phone: Phone number to logout
        """
        self.otp_service.clear_otp(phone)
