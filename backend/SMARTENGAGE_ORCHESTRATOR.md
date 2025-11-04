# SmartEngage Orchestrator - Implementation Complete ✅

## Overview

The SmartEngage Orchestrator is the core AI-powered customer reminder system for Sheba.xyz. It intelligently sends personalized Bengali reminder messages to customers whose booking cadence suggests they're ready to book again.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  SmartEngageOrchestrator                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Segmentation    →  Find eligible customers              │
│     (SegmentationService)                                    │
│                                                               │
│  2. Generation      →  OpenAI GPT-4o-mini (Bengali)         │
│     (OpenAI API + Retry Logic)                               │
│                                                               │
│  3. Safety          →  Filter inappropriate content          │
│     (SafetyFilter)                                           │
│                                                               │
│  4. Deep Links      →  JWT tokens with promo codes          │
│     (DeepLinkGenerator)                                      │
│                                                               │
│  5. Notification    →  Email via SMTP (HTML + Bengali)      │
│     (EmailNotificationProvider)                              │
│                                                               │
│  6. Persistence     →  Track in database (AIMessage)        │
│     (SQLAlchemy)                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Intelligent Segmentation
- **Booking Cadence**: Targets customers 21±1 days after last booking
- **Send Window**: Respects local time zones (9am-6pm)
- **Consent Filtering**: Only contacts customers who opted in
- **Frequency Caps**: Max 1 message per 24 hours

### 2. AI Message Generation
- **Model**: OpenAI GPT-4o-mini
- **Language**: Bengali (বাংলা) native script
- **Personalization**: 
  - Customer name
  - Last service name
  - Days since last booking
  - Promo code (if available)
- **Retry Logic**: 3 attempts with exponential backoff (2s → 4s → 8s)
- **Fallback**: Uses template if OpenAI fails

### 3. Safety Guardrails
- **Banned Phrases**: Profanity, scam terms (Bengali + English)
- **Tone Analysis**: Rejects aggressive/inappropriate messages
- **Length Limits**: 10-500 characters
- **Fallback Templates**: Safe generic messages if content rejected

### 4. Deep Links
- **JWT Tokens**: Time-limited (48h default)
- **Payload**: customer_id, service_id, promo_code, metadata
- **UTM Tracking**: utm_source=smartengage, utm_medium=email
- **Security**: HS256 signed, tamper-proof

### 5. Email Delivery
- **Format**: HTML with Bengali UTF-8 support
- **Styling**: Gradient header, clear CTA button, responsive design
- **Test Mode**: All emails redirect to navidkamal@iut-dhaka.edu
- **Template**: Includes promo code highlight, deep link, expiration notice

### 6. Tracking & Analytics
- **AIMessage Records**: Every message logged to database
- **Delivery Status**: PENDING → SENT → DELIVERED/FAILED
- **Correlation IDs**: End-to-end request tracking
- **Metadata**: Service, promo code, deep link, TTL hours

## Files Created

### Production Code
1. **src/ai/smartengage.py** (658 lines)
   - `SmartEngageOrchestrator` class
   - `generate_and_send_reminder()` - Single customer
   - `generate_and_send_bulk_reminders()` - Batch processing
   - `_generate_message_with_openai()` - AI generation with retry
   - `_apply_safety_filter()` - Content validation
   - `_build_email_html()` - HTML email template
   - `_build_reminder_prompt()` - OpenAI prompt construction

### Tests
2. **tests/unit/test_smartengage_orchestrator.py** (702 lines, 18 tests)
   - **Message Generation Tests** (4 tests)
     - OpenAI success/failure
     - Prompt building with/without promo
   - **Safety Filter Tests** (2 tests)
     - Pass clean messages
     - Reject inappropriate content
   - **Full Flow Tests** (7 tests)
     - Success scenario
     - Customer not found
     - No marketing consent
     - No booking history
     - OpenAI failure → fallback
     - Safety rejection → fallback
     - Notification failure
   - **Email HTML Tests** (2 tests)
     - With promo code
     - Without promo code
   - **Bulk Processing Tests** (2 tests)
     - Multiple customers
     - Mixed success/failure
   - **Factory Test** (1 test)
     - get_smartengage_orchestrator()

### Documentation
3. **backend/DEEPLINK_USAGE.md** (470 lines)
   - Usage examples
   - Integration patterns
   - Mobile app deep linking
   - Troubleshooting guide

## Test Results

```bash
tests/unit/test_smartengage_orchestrator.py
✅ test_generate_message_with_openai_success
✅ test_generate_message_openai_not_available
✅ test_build_reminder_prompt_with_promo
✅ test_build_reminder_prompt_without_promo
✅ test_apply_safety_filter_pass
✅ test_apply_safety_filter_reject
✅ test_generate_and_send_reminder_success
✅ test_generate_and_send_reminder_customer_not_found
✅ test_generate_and_send_reminder_no_consent
✅ test_generate_and_send_reminder_no_booking_history
✅ test_generate_and_send_reminder_openai_failure_uses_fallback
✅ test_generate_and_send_reminder_safety_rejection_uses_fallback
✅ test_generate_and_send_reminder_notification_failure
✅ test_build_email_html_with_promo
✅ test_build_email_html_without_promo
✅ test_generate_and_send_bulk_reminders
✅ test_generate_and_send_bulk_reminders_with_failures
✅ test_get_smartengage_orchestrator

======================= 18 PASSED, 66 warnings in 9.45s =======================
```

## Usage Example

### Single Customer Reminder

```python
from uuid import UUID
from src.lib.db import get_db
from src.ai.smartengage import get_smartengage_orchestrator

# Initialize orchestrator
db = next(get_db())
orchestrator = get_smartengage_orchestrator(db)

# Send reminder to specific customer
result = await orchestrator.generate_and_send_reminder(
    customer_id=UUID("..."),
    promo_code="RETURN15",
    ttl_hours=48,
)

if result["success"]:
    print(f"✅ Message sent: {result['message_id']}")
    print(f"📧 Email sent to customer with 48h deep link")
    print(f"🎯 Correlation ID: {result['correlation_id']}")
else:
    print(f"❌ Failed: {result['reason']}")
```

### Bulk Campaign

```python
# Send to all eligible customers (21-day cadence)
result = await orchestrator.generate_and_send_bulk_reminders(
    booking_cadence_days=21,
    send_window_start=9,   # 9am
    send_window_end=18,    # 6pm
    batch_size=50,         # Process 50 at a time
    promo_code="SPRING25",
)

print(f"Total eligible: {result['total_eligible']}")
print(f"✅ Sent: {result['sent']}")
print(f"❌ Failed: {result['failed']}")
print(f"⏭️  Skipped: {result['skipped']}")
```

## Integration Points

### Dependencies (Completed)
- ✅ **SegmentationService** (T032): Find eligible customers
- ✅ **DeepLinkGenerator** (T033): Create booking URLs
- ✅ **SafetyFilter**: Validate content (existing)
- ✅ **OpenAI Client**: Generate messages (existing)
- ✅ **EmailNotificationProvider**: Send emails (existing)

### Next Steps (T035-T041)
- **T035**: Campaign runner job (scheduled execution)
- **T036**: Internal API route (trigger endpoint)
- **T037**: Extended tracking (delivery events)
- **T038**: Event tracking (clicks, opens)
- **T039**: Template management (version control)
- **T040**: Configuration flags (A/B testing)
- **T041**: Metrics dashboard (observability)

## Error Handling

### Graceful Degradation
1. **OpenAI Failure**: Falls back to template message
2. **Safety Rejection**: Uses safe fallback template
3. **Notification Failure**: Marks message as FAILED, logs error
4. **Missing Data**: Returns descriptive error, skips customer

### Retry Logic
- **OpenAI API**: 3 attempts with exponential backoff
- **Email SMTP**: Single attempt (provider handles retries)

### Logging
- All operations logged with correlation_id
- DEBUG: Prompts, responses, decisions
- INFO: Status updates, milestones
- WARNING: Safety rejections, fallbacks used
- ERROR: Failures with stack traces

## Email Test Mode

**Currently Active**: All emails redirect to `navidkamal@iut-dhaka.edu`

### Test Email Features
- Yellow "TEST MODE" banner
- Shows original recipient
- Full production styling
- Bengali + English content

### To Disable (Production)
```python
# In src/services/notification_service.py
test_mode = False  # Change to False
test_email_override = None  # Or remove entirely
```

## Performance Characteristics

- **Single Customer**: ~2-3 seconds (OpenAI + SMTP)
- **Batch Processing**: Concurrent with batching (50 at a time)
- **Database Queries**: Optimized with JOINs and indexes
- **OpenAI Tokens**: ~150-200 tokens per message
- **Email Size**: ~8-12 KB HTML per message

## Security & Compliance

- ✅ **Marketing Consent**: Only contacts opted-in customers
- ✅ **Frequency Caps**: Max 1 message per 24 hours
- ✅ **Content Safety**: Multi-layer filtering
- ✅ **JWT Security**: Signed tokens, expiration enforced
- ✅ **Data Privacy**: No sensitive info in deep links
- ✅ **Unsubscribe**: Link included in footer (placeholder)

## Monitoring & Alerts

### Key Metrics to Track
- **Delivery Rate**: SENT / (SENT + FAILED)
- **Safety Rejection Rate**: Fallbacks / Total Messages
- **OpenAI Success Rate**: Generated / (Generated + Fallback)
- **Click-Through Rate**: Clicks / Sent
- **Conversion Rate**: Bookings / Sent

### Recommended Alerts
- OpenAI failure rate > 10%
- Email delivery failure > 5%
- Safety rejection rate > 15%
- No messages sent in 24h (if campaign scheduled)

---

## Summary

✅ **T034 Complete**: SmartEngage Orchestrator fully implemented and tested
- 658 lines of production code
- 702 lines of tests (18 tests, all passing)
- Complete error handling and fallbacks
- Ready for integration with campaign runner (T035)

**Status**: Ready for T035 (Campaign Runner Job) implementation.
