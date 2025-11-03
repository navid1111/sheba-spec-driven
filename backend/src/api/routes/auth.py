"""Authentication routes.

Provides OTP-based authentication endpoints:
- POST /auth/request-otp: Send OTP to email
- POST /auth/verify-otp: Verify OTP and get JWT token
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from src.lib.db import get_db
from src.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response Models
class RequestOTPRequest(BaseModel):
    """Request OTP payload - accepts email only."""
    email: str = Field(
        ...,
        description="Email address",
        examples=["user@example.com"]
    )


class RequestOTPResponse(BaseModel):
    """Request OTP response."""
    message: str = Field(default="OTP sent successfully")


class VerifyOTPRequest(BaseModel):
    """Verify OTP payload - accepts email only."""
    email: str = Field(..., description="Email address")
    code: str = Field(..., description="6-digit OTP code", min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    """Verify OTP response with JWT token."""
    token: str = Field(..., description="JWT access token")
    user_id: str = Field(..., description="User UUID")
    user_type: str = Field(..., description="User type (CUSTOMER, WORKER, ADMIN)")
    phone: Optional[str] = Field(None, description="User phone number")
    email: Optional[str] = Field(None, description="User email")


# Dependency to get AuthService
def get_auth_service(
    db: Session = Depends(get_db)
) -> AuthService:
    """Get AuthService instance with database session."""
    return AuthService(db)


# Routes
@router.post(
    "/request-otp",
    response_model=RequestOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Request OTP",
    description="Send OTP code to email for authentication"
)
async def request_otp(
    request: RequestOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Request OTP for email.
    
    Sends a 6-digit OTP code to the provided email address.
    Code is valid for 5 minutes.
    
    Args:
        request: Email address to send OTP to
        auth_service: Injected auth service
        
    Returns:
        Success message
        
    Raises:
        400: Invalid email format
        500: Failed to send OTP
    """
    try:
        success = await auth_service.request_otp(request.email)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP. Please try again."
            )
        
        return RequestOTPResponse()
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"❌ OTP Request Error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while sending OTP: {str(e)}"
        )


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP",
    description="Verify OTP code and receive JWT access token"
)
async def verify_otp(
    request: VerifyOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify OTP and get JWT token.
    
    Validates the OTP code for the phone number or email.
    If valid, creates user if they don't exist and returns JWT token.
    
    Args:
        request: Phone number/email and OTP code
        auth_service: Injected auth service
        
    Returns:
        JWT token and user information
        
    Raises:
        401: Invalid or expired OTP code
        500: Server error
    """
    try:
        result = await auth_service.verify_otp(request.email, request.code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP code"
            )
        
        return VerifyOTPResponse(**result)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print(f"❌ Verify OTP Error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during verification: {str(e)}"
        )

