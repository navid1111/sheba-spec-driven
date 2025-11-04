"""Tests for JWT utilities."""
import time
from datetime import timedelta

import pytest
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from src.lib.jwt import create_access_token, get_user_from_token, verify_token


def test_create_and_verify_token():
    """Test creating and verifying a valid token."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    user_type = "CUSTOMER"
    
    token = create_access_token(user_id, user_type)
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify the token
    payload = verify_token(token)
    assert payload["sub"] == user_id
    assert payload["user_type"] == user_type
    assert "iat" in payload
    assert "exp" in payload


def test_get_user_from_token():
    """Test extracting user info from token."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    user_type = "WORKER"
    
    token = create_access_token(user_id, user_type)
    
    extracted_id, extracted_type = get_user_from_token(token)
    assert extracted_id == user_id
    assert extracted_type == user_type


def test_expired_token():
    """Test that expired tokens are rejected."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    user_type = "ADMIN"
    
    # Create token that expires in 1 second
    token = create_access_token(user_id, user_type, expires_delta=timedelta(seconds=1))
    
    # Wait for it to expire
    time.sleep(2)
    
    # Should raise ExpiredSignatureError
    with pytest.raises(ExpiredSignatureError):
        verify_token(token)


def test_invalid_token():
    """Test that malformed tokens are rejected."""
    with pytest.raises(InvalidTokenError):
        verify_token("not.a.valid.token")


def test_tampered_token():
    """Test that tampered tokens are rejected."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    user_type = "CUSTOMER"
    
    token = create_access_token(user_id, user_type)
    
    # Tamper with the token by modifying a character
    tampered_token = token[:-5] + "XXXXX"
    
    # Should raise InvalidTokenError due to signature mismatch
    with pytest.raises(InvalidTokenError):
        verify_token(tampered_token)


def test_custom_expiry():
    """Test creating token with custom expiration time."""
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    user_type = "CUSTOMER"
    
    # Create token that expires in 1 hour
    token = create_access_token(user_id, user_type, expires_delta=timedelta(hours=1))
    
    payload = verify_token(token)
    
    # Check that expiry is approximately 1 hour from now
    exp_time = payload["exp"]
    iat_time = payload["iat"]
    diff = exp_time - iat_time
    
    # Should be close to 3600 seconds (1 hour)
    assert 3590 < diff < 3610  # Allow 10 second margin
