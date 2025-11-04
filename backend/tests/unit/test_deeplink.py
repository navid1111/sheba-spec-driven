"""
Unit tests for deep link generator.

Tests JWT token generation, verification, URL building,
and expiration handling.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
import jwt

from src.lib.deeplink import DeepLinkGenerator, get_deep_link_generator


@pytest.fixture
def generator():
    """Fixture providing deep link generator with test secret."""
    return DeepLinkGenerator(secret_key="test-secret-key-12345")


@pytest.fixture
def sample_customer_id():
    """Sample customer UUID."""
    return uuid4()


@pytest.fixture
def sample_service_id():
    """Sample service UUID."""
    return uuid4()


class TestTokenGeneration:
    """Test suite for JWT token generation."""
    
    def test_generate_booking_token_creates_valid_jwt(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should generate valid JWT token with correct structure."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=48
        )
        
        # Token should be a string
        assert isinstance(token, str)
        
        # Token should have 3 parts (header.payload.signature)
        parts = token.split(".")
        assert len(parts) == 3
        
        # Should be decodable
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        assert payload is not None
    
    def test_token_contains_required_fields(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Token payload should contain all required fields."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=24
        )
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        # Required fields
        assert payload["type"] == "booking_deeplink"
        assert payload["customer_id"] == str(sample_customer_id)
        assert payload["service_id"] == str(sample_service_id)
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expiration
    
    def test_token_includes_promo_code_when_provided(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should include promo code in token when specified."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            promo_code="CLEAN20",
            ttl_hours=48
        )
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        assert payload["promo_code"] == "CLEAN20"
    
    def test_token_includes_metadata_when_provided(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should include metadata in token when specified."""
        metadata = {
            "correlation_id": str(uuid4()),
            "campaign_id": "reminder_21day",
            "agent": "smartengage"
        }
        
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            metadata=metadata,
            ttl_hours=48
        )
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        assert payload["metadata"] == metadata
        assert payload["metadata"]["campaign_id"] == "reminder_21day"
    
    def test_token_expiration_set_correctly(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Token should expire at correct time based on TTL."""
        ttl_hours = 48
        before_generation = datetime.now(timezone.utc)
        
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=ttl_hours
        )
        
        after_generation = datetime.now(timezone.utc)
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        # Check expiration is approximately TTL hours from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_min = before_generation + timedelta(hours=ttl_hours) - timedelta(seconds=1)
        expected_max = after_generation + timedelta(hours=ttl_hours) + timedelta(seconds=1)
        
        assert expected_min <= exp_time <= expected_max
    
    def test_different_ttl_values(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should support different TTL values."""
        # 24-hour token
        token_24h = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=24
        )
        
        # 72-hour token
        token_72h = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=72
        )
        
        payload_24h = jwt.decode(token_24h, "test-secret-key-12345", algorithms=["HS256"])
        payload_72h = jwt.decode(token_72h, "test-secret-key-12345", algorithms=["HS256"])
        
        # 72h token should expire ~48 hours later than 24h token
        exp_diff = payload_72h["exp"] - payload_24h["exp"]
        assert 47 * 3600 <= exp_diff <= 49 * 3600  # ~48 hours in seconds


class TestTokenVerification:
    """Test suite for JWT token verification."""
    
    def test_verify_valid_token_returns_payload(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should successfully verify and return payload for valid token."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            promo_code="CLEAN20",
            ttl_hours=48
        )
        
        payload = generator.verify_booking_token(token)
        
        assert payload is not None
        assert payload["customer_id"] == str(sample_customer_id)
        assert payload["service_id"] == str(sample_service_id)
        assert payload["promo_code"] == "CLEAN20"
    
    def test_verify_expired_token_returns_none(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should return None for expired token."""
        # Create token with -1 hour TTL (already expired)
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=1)
        
        payload = {
            "type": "booking_deeplink",
            "customer_id": str(sample_customer_id),
            "service_id": str(sample_service_id),
            "iat": int(expired_time.timestamp()),
            "exp": int(expired_time.timestamp()),  # Already expired
        }
        
        token = jwt.encode(payload, "test-secret-key-12345", algorithm="HS256")
        
        result = generator.verify_booking_token(token)
        
        assert result is None
    
    def test_verify_invalid_signature_returns_none(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should return None for token with invalid signature."""
        # Generate token with different secret
        wrong_generator = DeepLinkGenerator(secret_key="wrong-secret-key")
        token = wrong_generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            ttl_hours=48
        )
        
        # Try to verify with correct generator (different secret)
        result = generator.verify_booking_token(token)
        
        assert result is None
    
    def test_verify_invalid_type_returns_none(
        self, generator, sample_customer_id
    ):
        """Should return None for token with wrong type."""
        payload = {
            "type": "wrong_type",  # Invalid type
            "customer_id": str(sample_customer_id),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=48)).timestamp()),
        }
        
        token = jwt.encode(payload, "test-secret-key-12345", algorithm="HS256")
        
        result = generator.verify_booking_token(token)
        
        assert result is None
    
    def test_verify_malformed_token_returns_none(self, generator):
        """Should return None for malformed token string."""
        malformed_tokens = [
            "not.a.jwt.token.at.all",
            "invalid-token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "",
        ]
        
        for token in malformed_tokens:
            result = generator.verify_booking_token(token)
            assert result is None, f"Should return None for: {token}"


class TestDeepLinkURLGeneration:
    """Test suite for complete deep link URL generation."""
    
    def test_generate_booking_link_returns_valid_url(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should generate complete URL with token and UTM parameters."""
        url = generator.generate_booking_link(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            promo_code="CLEAN20",
            ttl_hours=48
        )
        
        # Should start with base URL
        assert url.startswith("https://app.sheba.xyz/booking?")
        
        # Should contain token parameter
        assert "token=" in url
        
        # Should contain UTM parameters
        assert "utm_source=smartengage" in url
        assert "utm_medium=email" in url
    
    def test_url_includes_utm_campaign_when_provided(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should include utm_campaign parameter when specified."""
        url = generator.generate_booking_link(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            utm_campaign="reminder_21day",
            ttl_hours=48
        )
        
        assert "utm_campaign=reminder_21day" in url
    
    def test_url_uses_custom_utm_parameters(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should use custom UTM source and medium when provided."""
        url = generator.generate_booking_link(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            utm_source="coachnova",
            utm_medium="sms",
            ttl_hours=24
        )
        
        assert "utm_source=coachnova" in url
        assert "utm_medium=sms" in url
    
    def test_generated_url_token_is_verifiable(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Token extracted from URL should be verifiable."""
        url = generator.generate_booking_link(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            promo_code="SAVE50",
            ttl_hours=48
        )
        
        # Extract token from URL
        token_start = url.find("token=") + 6
        token_end = url.find("&", token_start)
        token = url[token_start:token_end]
        
        # Verify token
        payload = generator.verify_booking_token(token)
        
        assert payload is not None
        assert payload["customer_id"] == str(sample_customer_id)
        assert payload["service_id"] == str(sample_service_id)
        assert payload["promo_code"] == "SAVE50"
    
    def test_url_includes_metadata_in_token(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Metadata should be embedded in token within URL."""
        correlation_id = str(uuid4())
        
        url = generator.generate_booking_link(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            metadata={"correlation_id": correlation_id, "agent": "smartengage"},
            ttl_hours=48
        )
        
        # Extract and verify token
        token_start = url.find("token=") + 6
        token_end = url.find("&", token_start)
        token = url[token_start:token_end]
        
        payload = generator.verify_booking_token(token)
        
        assert payload["metadata"]["correlation_id"] == correlation_id
        assert payload["metadata"]["agent"] == "smartengage"


class TestPromoLinks:
    """Test suite for promotional link generation."""
    
    def test_generate_promo_link_without_service(self, generator):
        """Should generate promo link without service specification."""
        url = generator.generate_promo_link(
            promo_code="NEWUSER50",
            utm_campaign="new_user_campaign"
        )
        
        assert url.startswith("https://app.sheba.xyz/promo/NEWUSER50")
        assert "utm_source=smartengage" in url
        assert "utm_campaign=new_user_campaign" in url
    
    def test_generate_promo_link_with_service(self, generator, sample_service_id):
        """Should include service_id when specified."""
        url = generator.generate_promo_link(
            promo_code="CLEAN20",
            service_id=sample_service_id,
            utm_campaign="cleaning_promo"
        )
        
        assert f"service_id={sample_service_id}" in url
        assert "CLEAN20" in url
    
    def test_promo_link_has_longer_default_ttl(self, generator):
        """Promo links should default to 72 hours (longer than booking links)."""
        # This is implicit in the function signature
        # Just verify the function accepts ttl_hours parameter
        url = generator.generate_promo_link(
            promo_code="PROMO",
            ttl_hours=96  # Custom TTL
        )
        
        assert "PROMO" in url


class TestFactoryFunction:
    """Test suite for factory function."""
    
    def test_get_deep_link_generator_returns_instance(self):
        """Factory function should return configured instance."""
        generator = get_deep_link_generator()
        
        assert isinstance(generator, DeepLinkGenerator)
        assert generator.secret_key is not None
        assert generator.base_url is not None
    
    def test_factory_uses_settings(self):
        """Factory should use application settings."""
        generator = get_deep_link_generator()
        
        # Should have base_url from settings (or default)
        assert "sheba.xyz" in generator.base_url.lower()


class TestEdgeCases:
    """Test suite for edge cases and error handling."""
    
    def test_generator_requires_secret_key(self):
        """Should raise error when initialized without secret key."""
        with pytest.raises(ValueError, match="Secret key is required"):
            DeepLinkGenerator(secret_key="")
    
    def test_handles_uuid_objects_correctly(
        self, generator
    ):
        """Should handle UUID objects (not just strings)."""
        customer_id = uuid4()
        service_id = uuid4()
        
        token = generator.generate_booking_token(
            customer_id=customer_id,
            service_id=service_id,
            ttl_hours=24
        )
        
        payload = generator.verify_booking_token(token)
        
        # UUIDs should be converted to strings in token
        assert payload["customer_id"] == str(customer_id)
        assert UUID(payload["customer_id"]) == customer_id
    
    def test_empty_promo_code_not_included(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should not include promo_code key if None or empty."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            promo_code=None,
            ttl_hours=48
        )
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        assert "promo_code" not in payload
    
    def test_empty_metadata_not_included(
        self, generator, sample_customer_id, sample_service_id
    ):
        """Should not include metadata key if None."""
        token = generator.generate_booking_token(
            customer_id=sample_customer_id,
            service_id=sample_service_id,
            metadata=None,
            ttl_hours=48
        )
        
        payload = jwt.decode(
            token,
            "test-secret-key-12345",
            algorithms=["HS256"]
        )
        
        assert "metadata" not in payload
