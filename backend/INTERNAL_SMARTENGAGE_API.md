# Internal SmartEngage API Documentation

## Overview

The Internal SmartEngage API provides endpoints for triggering SmartEngage customer reminder campaigns programmatically. These endpoints are designed for internal service-to-service communication and scheduled job execution.

## Base URL

```
POST /internal/ai/smartengage/run-segment
```

## Authentication

**Development**: Currently accessible without authentication for testing and development.

**Production**: Should be protected with internal service tokens via `X-Internal-Token` header.

```http
X-Internal-Token: <internal-service-token>
```

## Endpoint: Trigger Campaign

### POST /internal/ai/smartengage/run-segment

Triggers a SmartEngage customer reminder campaign based on segment criteria or predefined preset.

#### Request Body

**Option 1: Custom Parameters**

```json
{
  "booking_cadence_days": 21,
  "send_window_start": 9,
  "send_window_end": 18,
  "batch_size": 50,
  "promo_code": "COMEBACK15"
}
```

**Option 2: Use Preset**

```json
{
  "preset": "aggressive"
}
```

#### Parameters

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| `booking_cadence_days` | integer | No | 21 | 7-90 | Days since last booking to target customers |
| `send_window_start` | integer | No | 9 | 0-23 | Hour to start sending (local time) |
| `send_window_end` | integer | No | 18 | 0-23 | Hour to stop sending (local time) |
| `batch_size` | integer | No | 50 | 1-1000 | Number of customers per batch |
| `promo_code` | string | No | null | max 50 chars | Optional promo code for messages |
| `preset` | enum | No | null | See presets | Use predefined configuration |

#### Campaign Presets

| Preset | Cadence (days) | Window (hours) | Batch Size | Promo Code |
|--------|---------------|----------------|------------|------------|
| `default` | 21 | 9-18 | 50 | none |
| `aggressive` | 14 | 9-20 | 100 | COMEBACK15 |
| `gentle` | 28 | 9-18 | 25 | none |
| `weekend` | 21 | 9-18 | 50 | WEEKEND20 |

**Note**: When `preset` is provided, it overrides all other parameters.

#### Response

**Success (202 Accepted)**

```json
{
  "status": "started",
  "correlation_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "SmartEngage campaign completed successfully",
  "campaign_result": {
    "total_eligible": 100,
    "sent": 95,
    "failed": 2,
    "skipped": 3,
    "duration_seconds": 12.5
  }
}
```

**Error (400 Bad Request)**

```json
{
  "error": "Invalid campaign parameters",
  "correlation_id": "..."
}
```

**Error (422 Validation Error)**

```json
{
  "error": "Validation error",
  "details": {
    "errors": [
      {
        "loc": ["body", "booking_cadence_days"],
        "msg": "Input should be greater than or equal to 7",
        "type": "greater_than_equal"
      }
    ]
  },
  "correlation_id": "..."
}
```

**Error (500 Internal Server Error)**

```json
{
  "error": "Campaign execution failed: <error details>",
  "correlation_id": "..."
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Campaign execution status: "started", "scheduled", "accepted" |
| `correlation_id` | UUID | Correlation ID for tracking campaign execution |
| `message` | string | Human-readable status message |
| `campaign_result` | object | Campaign execution results (if completed) |
| `campaign_result.total_eligible` | integer | Total customers matched segmentation criteria |
| `campaign_result.sent` | integer | Successfully sent messages |
| `campaign_result.failed` | integer | Failed message deliveries |
| `campaign_result.skipped` | integer | Skipped (consent/frequency caps) |
| `campaign_result.duration_seconds` | float | Campaign execution time |

## Usage Examples

### cURL: Trigger with Custom Parameters

```bash
curl -X POST http://localhost:8000/internal/ai/smartengage/run-segment \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: your-internal-token" \
  -d '{
    "booking_cadence_days": 21,
    "send_window_start": 9,
    "send_window_end": 18,
    "batch_size": 50,
    "promo_code": "COMEBACK15"
  }'
```

### cURL: Trigger with Preset

```bash
curl -X POST http://localhost:8000/internal/ai/smartengage/run-segment \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: your-internal-token" \
  -d '{
    "preset": "aggressive"
  }'
```

### Python: Using httpx

```python
import httpx

async def trigger_campaign():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": 21,
                "promo_code": "COMEBACK15"
            },
            headers={"X-Internal-Token": "your-internal-token"}
        )
        result = response.json()
        print(f"Campaign {result['correlation_id']}: {result['campaign_result']['sent']} sent")
```

### Python: Using requests (sync)

```python
import requests

def trigger_campaign():
    response = requests.post(
        "http://localhost:8000/internal/ai/smartengage/run-segment",
        json={"preset": "aggressive"},
        headers={"X-Internal-Token": "your-internal-token"}
    )
    result = response.json()
    return result["correlation_id"]
```

## Integration Patterns

### Scheduled Job Trigger

Use APScheduler or similar to trigger campaigns on a schedule:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=9, minute=0)
async def daily_campaign():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/internal/ai/smartengage/run-segment",
            json={"preset": "default"}
        )

scheduler.start()
```

### Event-Driven Trigger

Trigger campaigns based on business events (new service launch, special promotion):

```python
async def on_promotion_created(promo_code: str):
    """Trigger campaign when new promotion is created"""
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8000/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": 14,  # More aggressive for promo
                "promo_code": promo_code,
                "batch_size": 100  # Larger batches for time-sensitive promo
            }
        )
```

### A/B Testing Different Cadences

```python
async def run_ab_test():
    """Run A/B test with different cadences"""
    campaigns = [
        {"booking_cadence_days": 14, "promo_code": "TEST_A"},
        {"booking_cadence_days": 21, "promo_code": "TEST_B"},
        {"booking_cadence_days": 28, "promo_code": "TEST_C"},
    ]
    
    results = []
    async with httpx.AsyncClient() as client:
        for config in campaigns:
            response = await client.post(
                "http://localhost:8000/internal/ai/smartengage/run-segment",
                json=config
            )
            results.append(response.json())
    
    # Compare results
    for result in results:
        print(f"{result['campaign_result']['promo_code']}: "
              f"{result['campaign_result']['sent']} sent")
```

## Error Handling

### Recommended Error Handling Pattern

```python
import httpx

async def trigger_campaign_with_retry(preset: str, max_retries: int = 3):
    """Trigger campaign with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/internal/ai/smartengage/run-segment",
                    json={"preset": preset},
                    timeout=60.0  # 60 second timeout for campaign execution
                )
                
                if response.status_code == 202:
                    return response.json()
                elif response.status_code == 400:
                    # Invalid parameters - don't retry
                    raise ValueError(f"Invalid parameters: {response.json()}")
                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    raise Exception(f"Campaign failed after {max_retries} attempts")
                    
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
```

## Monitoring

### Track Campaign Results

Use the `correlation_id` to track campaign execution in logs:

```python
correlation_id = result["correlation_id"]
print(f"Track campaign: correlation_id={correlation_id}")

# Query logs
# grep "correlation_id: {correlation_id}" application.log
```

### Metrics to Monitor

- **Total Eligible**: Number of customers matching segmentation
- **Sent Rate**: `sent / total_eligible` (target: >90%)
- **Failed Rate**: `failed / total_eligible` (target: <5%)
- **Skipped Rate**: `skipped / total_eligible` (consent/frequency caps)
- **Duration**: Campaign execution time (target: <60s for 100 customers)

## Best Practices

1. **Use Presets for Standard Campaigns**: Leverage predefined presets for consistency
2. **Custom Parameters for Special Cases**: Use custom params for time-sensitive promotions
3. **Monitor Correlation IDs**: Always log and track correlation_id for debugging
4. **Respect Rate Limits**: Don't trigger multiple campaigns simultaneously
5. **Test with Dry Run**: Use `trigger_campaign_manual(dry_run=True)` for testing
6. **Handle Errors Gracefully**: Implement retry logic with exponential backoff
7. **Track Metrics**: Monitor sent/failed/skipped rates for optimization

## Testing

See test files for comprehensive examples:
- **Contract Tests**: `tests/contract/test_internal_smartengage_contract.py` (9 tests)
- **Integration Tests**: `tests/integration/test_internal_smartengage_integration.py` (8 tests)

## Related Documentation

- [SmartEngage Orchestrator](./SMARTENGAGE_ORCHESTRATOR.md)
- [Deep Link Usage](./DEEPLINK_USAGE.md)
- [Campaign Runner Job](../src/jobs/campaign_runner.py)
- [API Contract](../specs/001-shoktiai-platform/contracts/openapi.yaml)
