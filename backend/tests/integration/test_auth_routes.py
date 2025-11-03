"""Integration tests for authentication routes."""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


@pytest.mark.integration
def test_request_otp_success():
    """Test successful OTP request."""
    # Mock the auth service
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        mock_service.request_otp.return_value = True
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/request-otp",
            json={"phone": "+8801712345678"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "OTP sent successfully"


@pytest.mark.integration
def test_request_otp_invalid_phone():
    """Test OTP request with invalid phone."""
    # Mock the auth service to raise ValueError
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        mock_service.request_otp.side_effect = ValueError("Invalid phone number")
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/request-otp",
            json={"phone": "invalid"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
def test_request_otp_send_failure():
    """Test OTP request when send fails."""
    # Mock the auth service to return False
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        mock_service.request_otp.return_value = False
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/request-otp",
            json={"phone": "+8801712345678"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
def test_verify_otp_success():
    """Test successful OTP verification."""
    # Mock the auth service
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        mock_service.verify_otp.return_value = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_type": "CUSTOMER",
            "phone": "+8801712345678"
        }
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/verify-otp",
            json={
                "phone": "+8801712345678",
                "code": "123456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user_id" in data
        assert "user_type" in data
        assert data["user_type"] == "CUSTOMER"
        assert data["phone"] == "+8801712345678"


@pytest.mark.integration
def test_verify_otp_invalid_code():
    """Test OTP verification with invalid code."""
    # Mock the auth service to return None (invalid code)
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        mock_service.verify_otp.return_value = None
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/verify-otp",
            json={
                "phone": "+8801712345678",
                "code": "999999"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid or expired" in data["detail"]


@pytest.mark.integration
def test_verify_otp_missing_fields():
    """Test OTP verification with missing fields."""
    response = client.post(
        "/auth/verify-otp",
        json={"phone": "+8801712345678"}  # Missing 'code'
    )
    
    assert response.status_code == 422  # Validation error
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_verify_otp_invalid_code_length():
    """Test OTP verification with wrong code length."""
    response = client.post(
        "/auth/verify-otp",
        json={
            "phone": "+8801712345678",
            "code": "123"  # Too short
        }
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_full_auth_flow():
    """Test complete authentication flow."""
    phone = "+8801712345678"
    
    with patch("src.api.routes.auth.AuthService") as MockAuthService:
        mock_service = AsyncMock()
        
        # Step 1: Request OTP
        mock_service.request_otp.return_value = True
        MockAuthService.return_value = mock_service
        
        response = client.post(
            "/auth/request-otp",
            json={"phone": phone}
        )
        assert response.status_code == 200
        
        # Step 2: Verify OTP
        mock_service.verify_otp.return_value = {
            "token": "jwt_token_here",
            "user_id": "user-uuid",
            "user_type": "CUSTOMER",
            "phone": phone
        }
        
        response = client.post(
            "/auth/verify-otp",
            json={"phone": phone, "code": "123456"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
