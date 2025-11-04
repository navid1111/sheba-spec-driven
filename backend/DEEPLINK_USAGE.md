# Deep Link Generator - Usage Examples

## Overview

The `DeepLinkGenerator` creates time-limited JWT tokens for secure booking deep links. These tokens encode customer information, service details, and promotional codes that expire after a configurable period.

## Quick Start

```python
from uuid import UUID
from src.lib.deeplink import get_deep_link_generator

# Initialize generator
generator = get_deep_link_generator()

# Generate booking link
url = generator.generate_booking_link(
    customer_id=UUID("..."),
    service_id=UUID("..."),
    promo_code="CLEAN20",
    ttl_hours=48,
    utm_campaign="reminder_21day"
)

print(url)
# Output: https://app.sheba.xyz/booking?token=eyJ...&utm_source=smartengage&utm_medium=email&utm_campaign=reminder_21day
```

## Use Cases

### 1. SmartEngage Reminder (Most Common)

```python
# Customer: রহিম খান, last booked home cleaning 21 days ago
# Generate personalized booking link

url = generator.generate_booking_link(
    customer_id=customer.id,
    service_id=home_cleaning_service.id,
    promo_code="RETURN10",  # 10% off for returning customers
    ttl_hours=48,  # Link expires in 2 days
    utm_campaign="reminder_21day",
    metadata={
        "correlation_id": str(uuid4()),
        "agent": "smartengage",
        "segment": "home_cleaning_regular"
    }
)

# Include in email:
# "আবার বুক করতে এখানে ক্লিক করুন: {url}"
```

### 2. CoachNova Worker Recommendation

```python
# Worker needs encouragement to take breaks
# Generate booking link for self-care services

url = generator.generate_booking_link(
    customer_id=worker.user_id,  # Workers are also customers
    service_id=spa_service.id,
    promo_code="WELLNESS50",
    ttl_hours=72,  # 3 days for worker campaigns
    utm_source="coachnova",
    utm_medium="app_push",
    utm_campaign="burnout_prevention"
)
```

### 3. Promotional Broadcast (No Customer ID)

```python
# Send to email list or social media
# No customer_id, so users must login first

url = generator.generate_promo_link(
    promo_code="NEWUSER50",
    service_id=None,  # Any service
    ttl_hours=168,  # 1 week for broad campaigns
    utm_campaign="new_user_signup"
)

# Output: https://app.sheba.xyz/promo/NEWUSER50?utm_source=smartengage&utm_medium=email&utm_campaign=new_user_signup
```

### 4. Seasonal Campaign with Specific Service

```python
# Eid cleaning special
url = generator.generate_promo_link(
    promo_code="EID2025",
    service_id=deep_cleaning_service.id,  # Pre-select deep cleaning
    ttl_hours=336,  # 2 weeks (14 days)
    utm_campaign="eid_cleaning_2025"
)
```

## Token Structure

### Generated Token Payload

```json
{
  "type": "booking_deeplink",
  "customer_id": "uuid-string",
  "service_id": "uuid-string",
  "promo_code": "CLEAN20",
  "metadata": {
    "correlation_id": "uuid-string",
    "agent": "smartengage",
    "campaign_id": "reminder_21day"
  },
  "iat": 1699113600,  // Issued at (Unix timestamp)
  "exp": 1699286400   // Expires at (Unix timestamp)
}
```

### Token Security

- **Signed with HS256**: Tokens are signed with secret key, preventing tampering
- **Time-limited**: Tokens expire after TTL (default 48 hours)
- **One-time use recommended**: App should invalidate after booking
- **Includes metadata**: Correlation IDs for tracking and debugging

## URL Components

### Full URL Example

```
https://app.sheba.xyz/booking?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0eXBlIjoiYm9va2luZ19kZWVwbGluayIsImN1c3RvbWVyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwic2VydmljZV9pZCI6Ijk4N2Y2NTQzLWUyMWItMTJkMy1hNDU2LTQyNjYxNDE3NDAwMCIsInByb21vX2NvZGUiOiJDTEVBTjIwIiwiaWF0IjoxNjk5MTEzNjAwLCJleHAiOjE2OTkyODY0MDB9.abcdef123456&utm_source=smartengage&utm_medium=email&utm_campaign=reminder_21day
```

### UTM Parameters (Analytics)

- `utm_source`: Traffic source (smartengage, coachnova)
- `utm_medium`: Channel (email, sms, app_push)
- `utm_campaign`: Campaign identifier (reminder_21day, eid_2025)

## Token Verification

### Backend Endpoint (App)

```python
from src.lib.deeplink import get_deep_link_generator

@app.get("/booking")
async def handle_booking_link(token: str):
    generator = get_deep_link_generator()
    
    # Verify token
    payload = generator.verify_booking_token(token)
    
    if not payload:
        return {"error": "Invalid or expired link"}
    
    # Extract data
    customer_id = UUID(payload["customer_id"])
    service_id = UUID(payload["service_id"])
    promo_code = payload.get("promo_code")
    
    # Fetch customer and service from DB
    customer = db.get(Customer, customer_id)
    service = db.get(Service, service_id)
    
    # Pre-fill booking form
    return {
        "customer": customer.to_dict(),
        "service": service.to_dict(),
        "promo_code": promo_code,
        "discount": calculate_discount(promo_code)
    }
```

### Error Handling

```python
payload = generator.verify_booking_token(token)

if payload is None:
    # Token is invalid, expired, or tampered
    return {
        "error": "link_expired",
        "message": "This booking link has expired. Please request a new one."
    }

# Token is valid, proceed with booking
```

## Configuration

### Environment Variables (.env)

```bash
# Required
SECRET_KEY=your-secret-key-min-32-characters-long
APP_BASE_URL=https://app.sheba.xyz

# Optional (defaults shown)
# TTL handled per-link in code
```

### Customization

```python
# Custom secret key (for testing)
generator = DeepLinkGenerator(secret_key="test-key-12345")

# Custom TTL for specific campaign
url = generator.generate_booking_link(
    customer_id=customer.id,
    service_id=service.id,
    ttl_hours=96  # 4 days instead of default 48
)
```

## Integration with SmartEngage

### Email Template

```python
# In SmartEngage orchestrator
deep_link = generator.generate_booking_link(
    customer_id=customer.id,
    service_id=customer.last_service_id,
    promo_code="RETURN15",
    ttl_hours=48,
    utm_campaign="smartengage_reminder",
    metadata={
        "correlation_id": str(correlation_id),
        "agent": "smartengage",
        "booking_cadence_days": 21
    }
)

# Include in email
email_body = f"""
আপনার পরবর্তী {service.name_bn} সার্ভিসের জন্য সময় হয়ে গেছে!

বিশেষ অফার: 15% ছাড় (কোড: RETURN15)

এখনই বুক করুন: {deep_link}

লিংকটি পরবর্তী 48 ঘন্টার জন্য বৈধ।
"""
```

### Tracking Campaign Performance

```python
# When customer clicks link and completes booking
# Extract metadata from token

payload = generator.verify_booking_token(token)
correlation_id = payload["metadata"]["correlation_id"]

# Log conversion
analytics.track_conversion(
    correlation_id=correlation_id,
    customer_id=payload["customer_id"],
    service_id=payload["service_id"],
    campaign=payload["metadata"].get("segment"),
    conversion_time=datetime.utcnow()
)
```

## Testing

### Generate Test Link

```python
from src.lib.deeplink import DeepLinkGenerator
from uuid import uuid4

generator = DeepLinkGenerator(secret_key="test-secret")

test_url = generator.generate_booking_link(
    customer_id=uuid4(),
    service_id=uuid4(),
    promo_code="TEST50",
    ttl_hours=1,  # Short TTL for testing
    utm_campaign="test_campaign"
)

print(f"Test URL: {test_url}")
```

### Verify Test Link

```python
# Extract token from URL
token = test_url.split("token=")[1].split("&")[0]

# Verify
payload = generator.verify_booking_token(token)
print(f"Valid: {payload is not None}")
print(f"Customer: {payload['customer_id']}")
print(f"Promo: {payload['promo_code']}")
```

### Run Unit Tests

```bash
cd backend
pytest tests/unit/test_deeplink.py -v
# All 25 tests should pass
```

## Mobile App Integration

### iOS Deep Link Handling

```swift
// In AppDelegate or SceneDelegate
func application(_ app: UIApplication, open url: URL) -> Bool {
    if url.scheme == "shebaapp" && url.host == "booking" {
        let token = URLComponents(url: url)?.queryItems?
            .first(where: { $0.name == "token" })?.value
        
        if let token = token {
            // Verify with backend and show booking screen
            BookingManager.shared.handleDeepLink(token: token)
        }
    }
    return true
}
```

### Android Deep Link Handling

```kotlin
// In Activity
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    
    val data: Uri? = intent?.data
    if (data?.host == "booking") {
        val token = data.getQueryParameter("token")
        if (token != null) {
            // Verify and pre-fill booking
            BookingManager.handleDeepLink(token)
        }
    }
}
```

## Best Practices

1. **Short TTL for Security**: Use 24-48 hours for most links
2. **Include Metadata**: Add correlation_id for tracking
3. **Validate Before Use**: Always verify token on backend
4. **One-Time Use**: Invalidate token after successful booking
5. **Monitor Expiry**: Track how many customers click expired links
6. **A/B Testing**: Use different promo codes to test campaigns

## Troubleshooting

### "Invalid or expired link"

- Token TTL exceeded (default 48 hours)
- Token was tampered with (signature invalid)
- Wrong secret key used for verification
- Token format is malformed

### Links not opening in app

- Check deep link configuration in mobile app
- Verify URL scheme matches (shebaapp://)
- Test with universal links (https://) as fallback

### Promo code not applying

- Check if promo_code is in token payload
- Verify promo code exists and is active in database
- Check expiration date of promo code itself

---

**Status**: ✅ Deep link generator fully implemented and tested (25/25 tests passing)

**Next**: T034 - SmartEngage Orchestrator (uses this deep link generator)
