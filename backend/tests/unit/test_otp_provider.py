"""Tests for OTP provider service."""
import time
from unittest.mock import AsyncMock, patch

import pytest

from src.services.otp_provider import (
    ConsoleOTPProvider,
    OTPService,
    otp_service,
)


@pytest.mark.asyncio
async def test_console_provider_sends_otp():
    """Test console provider prints OTP."""
    provider = ConsoleOTPProvider()
    
    # Should always succeed
    result = await provider.send_otp("+8801712345678", "123456")
    assert result is True


@pytest.mark.asyncio
async def test_generate_code():
    """Test OTP code generation."""
    service = OTPService()
    
    code = service.generate_code()
    
    # Should be 6 digits
    assert len(code) == 6
    assert code.isdigit()
    
    # Generate multiple codes to test randomness
    codes = {service.generate_code() for _ in range(100)}
    # Should have variety (not all the same)
    assert len(codes) > 1


@pytest.mark.asyncio
async def test_request_and_verify_otp_success():
    """Test successful OTP request and verification flow."""
    service = OTPService()
    phone = "+8801712345678"
    
    # Mock the provider's send_otp to avoid actual email/SMS sending
    with patch.object(service.provider, 'send_otp', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Request OTP
        success = await service.request_otp(phone)
        assert success is True
    
    # Get the code that was generated (from internal store)
    # In real test, we'd intercept the send
    # For now, we'll patch the provider
    with patch.object(service.provider, 'send_otp', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Request again and capture code
        code = service.generate_code()
        await service.request_otp(phone)
        
        # Manually set the code for testing
        hashed = service._hash_code(code)
        expiry = service._store[phone][1]
        service._store[phone] = (hashed, expiry)
        
        # Verify the code
        result = await service.verify_otp(phone, code)
        assert result is True
        
        # Code should be cleared after use
        assert phone not in service._store


@pytest.mark.asyncio
async def test_verify_otp_wrong_code():
    """Test OTP verification with wrong code."""
    service = OTPService()
    phone = "+8801712345678"
    
    # Mock the provider's send_otp to avoid actual email/SMS sending
    with patch.object(service.provider, 'send_otp', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Request OTP
        await service.request_otp(phone)
    
    # Try wrong code
    result = await service.verify_otp(phone, "999999")
    assert result is False
    
    # Code should still be in store (not cleared on failure)
    assert phone in service._store


@pytest.mark.asyncio
async def test_verify_otp_expired():
    """Test OTP verification with expired code."""
    # Use service with 1-second TTL
    with patch("src.services.otp_provider.settings.otp_ttl_seconds", 1):
        service = OTPService()
        phone = "+8801712345678"
        
        # Request OTP
        await service.request_otp(phone)
        
        # Wait for expiration
        time.sleep(2)
        
        # Try to verify - should fail due to expiration
        result = await service.verify_otp(phone, "123456")
        assert result is False
        
        # Should be cleaned up
        assert phone not in service._store


@pytest.mark.asyncio
async def test_verify_otp_no_request():
    """Test verifying OTP without prior request."""
    service = OTPService()
    phone = "+8801712345678"
    
    # Verify without requesting
    result = await service.verify_otp(phone, "123456")
    assert result is False


@pytest.mark.asyncio
async def test_request_otp_invalid_phone():
    """Test requesting OTP with invalid phone number."""
    service = OTPService()
    
    with pytest.raises(ValueError, match="Invalid phone number"):
        await service.request_otp("")
    
    with pytest.raises(ValueError, match="Invalid phone number"):
        await service.request_otp("123")


@pytest.mark.asyncio
async def test_clear_otp():
    """Test clearing OTP for a phone number."""
    service = OTPService()
    phone = "+8801712345678"
    
    # Mock the provider's send_otp to avoid actual email/SMS sending
    with patch.object(service.provider, 'send_otp', new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        
        # Request OTP
        await service.request_otp(phone)
        assert phone in service._store
    
    # Clear it
    service.clear_otp(phone)
    assert phone not in service._store
    
    # Clearing non-existent OTP should not error
    service.clear_otp(phone)


@pytest.mark.asyncio
async def test_global_otp_service():
    """Test that global otp_service instance is properly initialized."""
    assert otp_service is not None
    assert isinstance(otp_service, OTPService)
    assert otp_service.provider is not None
