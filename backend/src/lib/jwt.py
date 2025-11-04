"""JWT token generation and validation utilities.

Uses HS256 algorithm with secret from settings.
Tokens include standard claims (exp, iat, sub) plus custom user_type claim.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt.exceptions import InvalidTokenError

from src.lib.settings import settings


# Token expiration time (24 hours by default)
TOKEN_EXPIRY_HOURS = 24


def create_access_token(
    user_id: str,
    user_type: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token for a user.
    
    Args:
        user_id: UUID of the user (stored in 'sub' claim)
        user_type: Type of user (CUSTOMER, WORKER, ADMIN)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token("123e4567-e89b-12d3-a456-426614174000", "CUSTOMER")
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=TOKEN_EXPIRY_HOURS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,  # Subject: user ID
        "user_type": user_type,  # Custom claim for authorization
        "iat": now,  # Issued at
        "exp": expire,  # Expiration time
    }
    
    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload with claims
        
    Raises:
        InvalidTokenError: If token is invalid, expired, or signature doesn't match
        
    Example:
        >>> payload = verify_token(token)
        >>> user_id = payload["sub"]
        >>> user_type = payload["user_type"]
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return payload
    except InvalidTokenError as e:
        # Re-raise with original exception for caller to handle
        # (expired, invalid signature, malformed token, etc.)
        raise e


def get_user_from_token(token: str) -> tuple[str, str]:
    """Extract user_id and user_type from a token.
    
    Convenience function that verifies token and extracts user info.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (user_id, user_type)
        
    Raises:
        InvalidTokenError: If token is invalid
        KeyError: If required claims are missing
        
    Example:
        >>> user_id, user_type = get_user_from_token(token)
    """
    payload = verify_token(token)
    user_id = payload["sub"]
    user_type = payload["user_type"]
    return user_id, user_type
