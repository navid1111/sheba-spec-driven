"""Tests for authentication service."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.models.users import User, UserType
from src.services.auth_service import AuthService


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def auth_service(mock_session):
    """Create auth service instance with mocked session."""
    return AuthService(mock_session)


@pytest.mark.asyncio
async def test_request_otp_success(auth_service):
    """Test successful OTP request."""
    email = "test@example.com"
    
    # Mock the OTP service
    with patch.object(auth_service.otp_service, 'request_otp', new_callable=AsyncMock) as mock_otp:
        mock_otp.return_value = True
        
        result = await auth_service.request_otp(email)
        
        assert result is True
        mock_otp.assert_called_once_with(email)


@pytest.mark.asyncio
async def test_request_otp_invalid_email(auth_service):
    """Test OTP request with invalid email address."""
    # Invalid email format
    with pytest.raises(ValueError, match="Invalid email address"):
        await auth_service.request_otp("not-an-email")
    
    # Empty email
    with pytest.raises(ValueError, match="Invalid email address"):
        await auth_service.request_otp("")


@pytest.mark.asyncio
async def test_verify_otp_creates_new_user(auth_service, mock_session):
    """Test OTP verification creates new user."""
    email = "test@example.com"
    code = "123456"
    
    # Mock OTP verification to succeed
    with patch.object(auth_service.otp_service, 'verify_otp', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        # Mock database query to return no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await auth_service.verify_otp(email, code)
        
        assert result is not None
        assert "token" in result
        assert result["email"] == email
        assert result["user_type"] == "customer"
        
        token = result["token"]
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify user was added to session
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_verify_otp_existing_user(auth_service, mock_session):
    """Test OTP verification with existing user."""
    email = "test@example.com"
    code = "123456"
    user_id = uuid4()
    
    # Create mock existing user
    existing_user = MagicMock(spec=User)
    existing_user.id = user_id
    existing_user.email = email
    existing_user.type = MagicMock()
    existing_user.type.value = "worker"  # Mock enum value
    existing_user.last_login_at = None
    
    # Mock OTP verification
    with patch.object(auth_service.otp_service, 'verify_otp', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        # Mock database query to return existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = mock_result
        
        result = await auth_service.verify_otp(email, code)
        
        assert result is not None
        assert result["user_id"] == str(user_id)
        assert result["user_type"] == "worker"
        assert result["email"] == email
        
        # Verify last_login_at was updated
        assert existing_user.last_login_at is not None
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_verify_otp_invalid_code(auth_service):
    """Test OTP verification with invalid code."""
    email = "test@example.com"
    code = "999999"
    
    # Mock OTP verification to fail
    with patch.object(auth_service.otp_service, 'verify_otp', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False
        
        result = await auth_service.verify_otp(email, code)
        
        assert result is None


@pytest.mark.asyncio
async def test_verify_otp_custom_user_type(auth_service, mock_session):
    """Test creating user with custom user type."""
    email = "test@example.com"
    code = "123456"
    
    # Mock OTP verification
    with patch.object(auth_service.otp_service, 'verify_otp', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True
        
        # Mock database query to return no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await auth_service.verify_otp(email, code, user_type="ADMIN")
        
        assert result is not None
        assert result["user_type"] == "admin"


@pytest.mark.asyncio
async def test_logout(auth_service):
    """Test logout clears OTP."""
    email = "test@example.com"
    
    with patch.object(auth_service.otp_service, 'clear_otp', new_callable=AsyncMock) as mock_clear:
        await auth_service.logout(email)
        
        mock_clear.assert_called_once_with(email)


@pytest.mark.asyncio
async def test_full_auth_flow(auth_service, mock_session):
    """Test complete authentication flow: request OTP -> verify -> get token."""
    email = "test@example.com"
    
    # Mock OTP service
    with patch.object(auth_service.otp_service, 'request_otp', new_callable=AsyncMock) as mock_request, \
         patch.object(auth_service.otp_service, 'verify_otp', new_callable=AsyncMock) as mock_verify:
        
        mock_request.return_value = True
        mock_verify.return_value = True
        
        # Mock database for verify step
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Step 1: Request OTP
        request_success = await auth_service.request_otp(email)
        assert request_success is True
        
        # Step 2: Verify OTP and get token
        result = await auth_service.verify_otp(email, "123456")
        assert result is not None
        assert "token" in result
        
        # Step 3: Verify token can be decoded
        from src.lib.jwt import verify_token
        payload = verify_token(result["token"])
        assert payload["sub"] == result["user_id"]
        assert payload["user_type"] == result["user_type"]
