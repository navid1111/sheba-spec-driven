"""
API dependencies for FastAPI dependency injection.

Provides common dependencies like database sessions and authentication.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.db import get_db as get_db_session
from src.lib.jwt import verify_token
from src.models.users import User


# Re-export get_db for convenience
get_db = get_db_session


# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: Bearer token from Authorization header
        db: Database session
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: 401 if token invalid or user not found
    """
    from sqlalchemy import select
    
    try:
        # Decode JWT token
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")  # JWT standard: user_id in 'sub' claim
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Query user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, None otherwise.
    
    Useful for endpoints that work with or without authentication.
    
    Args:
        credentials: Optional bearer token
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
