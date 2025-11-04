"""
Deep link generator for SmartEngage booking flows.

Creates time-limited JWT tokens that encode:
- Customer ID (for pre-filled user info)
- Service ID (for direct service selection)
- Promo code (optional discount)
- Expiration timestamp

The token is used to generate deep links like:
https://app.sheba.xyz/booking?token=eyJ...&utm_source=smartengage
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import jwt

from src.lib.settings import settings
from src.lib.logging import get_logger


logger = get_logger(__name__)


class DeepLinkGenerator:
    """
    Generate time-limited deep links for booking flows.
    
    Uses JWT tokens to securely encode booking parameters that expire
    after a configurable time period (default 48 hours).
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize deep link generator.
        
        Args:
            secret_key: JWT signing key (defaults to settings.secret_key)
        """
        # Use provided secret_key or fall back to settings
        if secret_key is not None:
            self.secret_key = secret_key
        else:
            self.secret_key = settings.secret_key
        
        # Validate secret key is not empty
        if not self.secret_key or self.secret_key == "":
            raise ValueError("Secret key is required for JWT signing")
        
        self.algorithm = "HS256"
        self.base_url = settings.app_base_url or "https://app.sheba.xyz"
        
        logger.info("DeepLinkGenerator initialized", extra={"base_url": self.base_url})
    
    def generate_booking_token(
        self,
        customer_id: UUID,
        service_id: UUID,
        promo_code: Optional[str] = None,
        ttl_hours: int = 48,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Generate JWT token for booking deep link.
        
        Args:
            customer_id: Customer UUID for pre-filled user info
            service_id: Service UUID to book
            promo_code: Optional promotional code for discount
            ttl_hours: Token validity in hours (default 48)
            metadata: Optional additional data (correlation_id, campaign_id, etc.)
        
        Returns:
            JWT token string
        
        Example:
            >>> token = generator.generate_booking_token(
            ...     customer_id=UUID("..."),
            ...     service_id=UUID("..."),
            ...     promo_code="CLEAN20",
            ...     ttl_hours=48
            ... )
            >>> print(token)
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        """
        now = datetime.now(timezone.utc)
        expiration = now + timedelta(hours=ttl_hours)
        
        # Build JWT payload
        payload = {
            "type": "booking_deeplink",
            "customer_id": str(customer_id),
            "service_id": str(service_id),
            "iat": int(now.timestamp()),
            "exp": int(expiration.timestamp()),
        }
        
        # Add optional fields
        if promo_code:
            payload["promo_code"] = promo_code
        
        if metadata:
            payload["metadata"] = metadata
        
        # Generate JWT token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.info(
            "Generated booking token",
            extra={
                "customer_id": str(customer_id),
                "service_id": str(service_id),
                "ttl_hours": ttl_hours,
                "expires_at": expiration.isoformat(),
            }
        )
        
        return token
    
    def verify_booking_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode booking token.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload dict if valid, None if invalid/expired
        
        Example:
            >>> payload = generator.verify_booking_token(token)
            >>> if payload:
            ...     customer_id = UUID(payload["customer_id"])
            ...     service_id = UUID(payload["service_id"])
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Validate payload type
            if payload.get("type") != "booking_deeplink":
                logger.warning("Invalid token type", extra={"type": payload.get("type")})
                return None
            
            logger.info(
                "Token verified successfully",
                extra={
                    "customer_id": payload.get("customer_id"),
                    "service_id": payload.get("service_id"),
                }
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def generate_booking_link(
        self,
        customer_id: UUID,
        service_id: UUID,
        promo_code: Optional[str] = None,
        ttl_hours: int = 48,
        utm_source: str = "smartengage",
        utm_medium: str = "email",
        utm_campaign: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Generate complete booking deep link URL with token.
        
        Args:
            customer_id: Customer UUID
            service_id: Service UUID
            promo_code: Optional promo code
            ttl_hours: Token validity hours
            utm_source: UTM source for analytics (default: smartengage)
            utm_medium: UTM medium for analytics (default: email)
            utm_campaign: UTM campaign name (optional)
            metadata: Optional metadata (correlation_id, etc.)
        
        Returns:
            Complete deep link URL
        
        Example:
            >>> url = generator.generate_booking_link(
            ...     customer_id=UUID("..."),
            ...     service_id=UUID("..."),
            ...     promo_code="CLEAN20",
            ...     utm_campaign="reminder_21day"
            ... )
            >>> print(url)
            'https://app.sheba.xyz/booking?token=eyJ...&utm_source=smartengage&...'
        """
        # Generate token
        token = self.generate_booking_token(
            customer_id=customer_id,
            service_id=service_id,
            promo_code=promo_code,
            ttl_hours=ttl_hours,
            metadata=metadata
        )
        
        # Build URL with query parameters
        url_parts = [f"{self.base_url}/booking?token={token}"]
        
        # Add UTM parameters for analytics
        url_parts.append(f"utm_source={utm_source}")
        url_parts.append(f"utm_medium={utm_medium}")
        
        if utm_campaign:
            url_parts.append(f"utm_campaign={utm_campaign}")
        
        url = "&".join(url_parts)
        
        logger.info(
            "Generated booking deep link",
            extra={
                "customer_id": str(customer_id),
                "service_id": str(service_id),
                "url_length": len(url),
                "utm_source": utm_source,
            }
        )
        
        return url
    
    def generate_promo_link(
        self,
        promo_code: str,
        service_id: Optional[UUID] = None,
        ttl_hours: int = 72,
        utm_campaign: Optional[str] = None
    ) -> str:
        """
        Generate promotional link without customer ID (for broadcast campaigns).
        
        Args:
            promo_code: Promotional code
            service_id: Optional service to pre-select
            ttl_hours: Token validity hours (default 72 for promos)
            utm_campaign: Campaign identifier
        
        Returns:
            Promotional deep link URL
        
        Example:
            >>> url = generator.generate_promo_link(
            ...     promo_code="NEWUSER50",
            ...     utm_campaign="new_user_campaign"
            ... )
        """
        # For promo links without customer_id, use a special marker
        # The app will detect this and show signup/login flow
        url_parts = [f"{self.base_url}/promo/{promo_code}"]
        
        # Add service if specified
        if service_id:
            url_parts[0] += f"?service_id={service_id}"
            connector = "&"
        else:
            connector = "?"
        
        # Add UTM parameters
        utm_params = [
            f"utm_source=smartengage",
            f"utm_medium=email",
        ]
        
        if utm_campaign:
            utm_params.append(f"utm_campaign={utm_campaign}")
        
        url = url_parts[0] + connector + "&".join(utm_params)
        
        logger.info(
            "Generated promo link",
            extra={
                "promo_code": promo_code,
                "service_id": str(service_id) if service_id else None,
                "url_length": len(url),
            }
        )
        
        return url


# Factory function
def get_deep_link_generator() -> DeepLinkGenerator:
    """
    Get DeepLinkGenerator instance.
    
    Returns:
        DeepLinkGenerator instance configured with app settings
    """
    return DeepLinkGenerator()
