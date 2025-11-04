# ShoktiAI Platform - Application Guide

**Version**: 1.0.0  
**Last Updated**: November 5, 2025  
**Status**: US1 SmartEngage Complete (13/13 tasks)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Modules](#core-modules)
4. [User Stories & Features](#user-stories--features)
5. [API Endpoints](#api-endpoints)
6. [Database Models](#database-models)
7. [Services & Business Logic](#services--business-logic)
8. [AI Agents](#ai-agents)
9. [Background Jobs](#background-jobs)
10. [Configuration & Settings](#configuration--settings)

---

## Overview

ShoktiAI is an AI-powered customer engagement and worker coaching platform for Sheba, a Bangladeshi home services marketplace. The platform uses AI to send personalized Bengali reminders to customers and provide empathetic coaching to workers.

### Key Capabilities

- **SmartEngage**: AI-generated Bengali reminders for customers approaching their service renewal window
- **CoachNova**: (Planned) AI-powered coaching for workers with performance issues
- **Analytics Dashboard**: (Planned) Metrics and insights for operations managers
- **Observability**: Prometheus-compatible metrics for monitoring

### Technology Stack

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL (Neon serverless)
- **AI**: OpenAI GPT-4o-mini
- **Messaging**: Twilio (SMS), Email (SMTP)
- **Scheduling**: APScheduler
- **Monitoring**: Prometheus metrics
- **Authentication**: JWT + OTP

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Auth API   │  │  Admin API   │  │ Internal API │      │
│  │  (Public)    │  │  (Admin)     │  │  (Scheduled) │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│  ┌──────▼──────────────────▼──────────────────▼───────┐      │
│  │              Service Layer                         │      │
│  │  • AuthService    • NotificationService            │      │
│  │  • SegmentationService  • MetricsCollector         │      │
│  └──────┬─────────────────────────────────┬───────────┘      │
│         │                                  │                  │
│  ┌──────▼──────────────────────────────────▼───────────┐      │
│  │              AI Orchestrators                      │      │
│  │  • SmartEngageOrchestrator (Bengali reminders)    │      │
│  │  • OpenAI Client (GPT-4o-mini)                     │      │
│  │  • SafetyFilter (content moderation)               │      │
│  └──────┬─────────────────────────────────────────────┘      │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────┐      │
│  │           Background Jobs & Scheduler               │      │
│  │  • Campaign Runner (daily 9 AM UTC)                 │      │
│  │  • APScheduler + PostgreSQL Advisory Locks         │      │
│  └──────┬──────────────────────────────────────────────┘      │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────┐      │
│  │              PostgreSQL Database                    │      │
│  │  • Users, Customers, Workers, Services, Bookings    │      │
│  │  • AI Messages, User Events, Campaigns              │      │
│  └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### 1. Authentication System (`src/lib/jwt.py`, `src/services/auth_service.py`)

**Purpose**: Secure user authentication via OTP (One-Time Password)

#### Functions:

##### `create_access_token(data: dict, expires_minutes: int = 30) -> str`
Creates a JWT access token with user data.

**User Story**: *As a user, I want to securely log in to the platform so that my data is protected.*

**Example**:
```python
from src.lib.jwt import create_access_token

token = create_access_token({"sub": str(user_id), "type": "customer"})
# Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

##### `verify_token(token: str) -> dict | None`
Verifies JWT token and returns payload.

**User Story**: *As a user, I want my session to remain secure and automatically expire after a period of time.*

**Example**:
```python
from src.lib.jwt import verify_token

payload = verify_token(token)
# Returns: {"sub": "user-id", "type": "customer", "exp": 1234567890}
```

##### `AuthService.request_otp(email: str, user_type: str = "customer") -> dict`
Generates and sends OTP code to user's email.

**User Story**: *As a customer, I want to receive a one-time code via email so I can log in without a password.*

**Example**:
```python
from src.services.auth_service import AuthService

result = await auth_service.request_otp("customer@example.com")
# Returns: {"status": "sent", "message": "OTP sent to customer@example.com"}
# OTP sent via email or console (dev mode)
```

##### `AuthService.verify_otp(email: str, code: str, user_type: str = "customer") -> dict`
Verifies OTP and issues JWT token.

**User Story**: *As a customer, I want to enter my OTP code and receive access to my account.*

**Example**:
```python
result = await auth_service.verify_otp("customer@example.com", "123456")
# Returns: {
#   "access_token": "eyJhbGci...",
#   "token_type": "bearer",
#   "user": {...}
# }
```

---

### 2. Notification System (`src/services/notification_service.py`)

**Purpose**: Send SMS, email, and push notifications to users

#### Functions:

##### `NotificationService.send(channel: MessageChannel, to: str, message: str, ...) -> str`
Sends notification via specified channel and creates AIMessage record.

**User Story**: *As a customer, I want to receive personalized reminders via email so I don't miss my service renewal.*

**Example**:
```python
from src.services.notification_service import NotificationService, MessageChannel

message_id = await notification_service.send(
    channel=MessageChannel.EMAIL,
    to="customer@example.com",
    message="আপনার সার্ভিসের সময় হয়েছে!",
    subject="সার্ভিস রিমাইন্ডার",
    user_id=user_id,
    agent_type="smartengage"
)
# Returns: UUID of created AIMessage
```

##### `NotificationService.update_delivery_status(message_id: UUID, status: DeliveryStatus, ...)`
Updates delivery status of sent message.

**User Story**: *As an operations manager, I want to track message delivery status so I can monitor campaign effectiveness.*

**Example**:
```python
await notification_service.update_delivery_status(
    message_id=message_id,
    status=DeliveryStatus.DELIVERED,
    provider_response={"twilio_sid": "SM1234..."}
)
```

---

### 3. Consent & Frequency Management (`src/lib/consent.py`)

**Purpose**: Respect user preferences and prevent message fatigue

#### Functions:

##### `check_consent(db: Session, user_id: UUID, channel: MessageChannel, role: MessageRole) -> tuple[bool, str | None]`
Checks if user has consented to receive messages.

**User Story**: *As a customer, I want to control which types of messages I receive so I'm not overwhelmed.*

**Example**:
```python
from src.lib.consent import check_consent, MessageChannel, MessageRole

allowed, reason = await check_consent(
    db=db,
    user_id=customer_id,
    channel=MessageChannel.SMS,
    role=MessageRole.CUSTOMER
)
# Returns: (True, None) if consented
# Returns: (False, "No consent for SMS") if not consented
```

##### `check_frequency_cap(db: Session, user_id: UUID, channel: MessageChannel, role: MessageRole, caps: dict = None) -> tuple[bool, str | None]`
Checks if user has exceeded frequency limits.

**User Story**: *As a customer, I want to receive reminders at a reasonable frequency so I don't feel spammed.*

**Example**:
```python
from src.lib.consent import check_frequency_cap

allowed, reason = await check_frequency_cap(
    db=db,
    user_id=customer_id,
    channel=MessageChannel.SMS,
    role=MessageRole.CUSTOMER
)
# Returns: (True, None) if under limits
# Returns: (False, "Daily cap exceeded: 2/1 messages") if over limit
```

##### `can_send_notification(db: Session, user_id: UUID, channel: MessageChannel, role: MessageRole, caps: dict = None) -> tuple[bool, str | None]`
Combined check for consent + frequency caps.

**User Story**: *As a system, I want to ensure all compliance checks pass before sending any message.*

**Example**:
```python
allowed, reason = await can_send_notification(
    db=db,
    user_id=customer_id,
    channel=MessageChannel.EMAIL,
    role=MessageRole.CUSTOMER
)
# Returns: (True, None) if all checks pass
```

---

### 4. Configuration System (`src/lib/config_flags.py`)

**Purpose**: Centralized configuration for frequency caps, feature flags, and campaign presets

#### Classes & Functions:

##### `FrequencyCaps` (Pydantic Model)
Configurable frequency limits aligned with research.md specs.

**User Story**: *As an operations manager, I want to configure message frequency limits without code changes so I can respond to user feedback quickly.*

**Example**:
```python
from src.lib.config_flags import FrequencyCaps, get_frequency_caps

caps = get_frequency_caps()
# Returns: FrequencyCaps(
#   customer_daily_limit=1,
#   customer_weekly_limit=2,
#   worker_weekly_limit=1,
#   ...
# )
```

##### `FeatureFlags` (Pydantic Model)
Enable/disable features for A/B testing and rollout control.

**User Story**: *As a product manager, I want to enable/disable features without deploying code so I can run A/B tests safely.*

**Example**:
```python
from src.lib.config_flags import get_feature_flags

flags = get_feature_flags()
if flags.smartengage_enabled:
    # Run SmartEngage campaign
    pass
```

##### `CampaignPresets` (Pydantic Model)
Pre-configured campaign settings (default, aggressive, gentle, weekend).

**User Story**: *As a marketing manager, I want to quickly launch campaigns with proven settings so I don't have to configure each parameter manually.*

**Example**:
```python
from src.lib.config_flags import get_campaign_presets

presets = get_campaign_presets()
aggressive = presets.aggressive
# Returns: CampaignPreset(
#   cadence_days=14,
#   batch_size=200,
#   send_window="8-20"
# )
```

---

### 5. Deep Link Generator (`src/lib/deeplink.py`)

**Purpose**: Create time-limited, trackable links for booking flow

#### Functions:

##### `DeepLinkGenerator.generate_booking_link(customer_id: UUID, service_id: UUID, promo_code: str = None, ...) -> str`
Generates deep link with JWT token for secure booking.

**User Story**: *As a customer, I want to click a link in my reminder email and go directly to the booking page with my service pre-filled.*

**Example**:
```python
from src.lib.deeplink import get_deep_link_generator

generator = get_deep_link_generator()
link = generator.generate_booking_link(
    customer_id=customer_id,
    service_id=service_id,
    promo_code="SAVE20",
    ttl_hours=48,
    utm_campaign="smartengage_reminder"
)
# Returns: "https://app.sheba.xyz/book?token=eyJhbGci...&utm_campaign=smartengage_reminder"
```

##### `DeepLinkGenerator.verify_booking_token(token: str) -> dict | None`
Verifies token and returns payload.

**User Story**: *As a system, I want to validate booking tokens to prevent unauthorized access and expired links.*

**Example**:
```python
payload = generator.verify_booking_token(token)
# Returns: {
#   "customer_id": "uuid",
#   "service_id": "uuid",
#   "promo_code": "SAVE20",
#   "type": "booking",
#   "exp": 1234567890
# }
```

##### `DeepLinkGenerator.generate_promo_link(customer_id: UUID, promo_code: str, service_id: UUID = None, ...) -> str`
Generates promo link without specific service (broadcast campaigns).

**User Story**: *As a marketing manager, I want to send promo codes that work for any service so customers have flexibility.*

**Example**:
```python
link = generator.generate_promo_link(
    customer_id=customer_id,
    promo_code="WEEKEND50",
    ttl_hours=72
)
# Returns: "https://app.sheba.xyz/book?token=eyJhbGci..."
```

---

### 6. Segmentation Service (`src/services/segmentation_service.py`)

**Purpose**: Identify eligible customers for targeted campaigns

#### Functions:

##### `SegmentationService.identify_eligible_customers(cadence_days: int = 21, send_window: str = "9-18", ...) -> list[UUID]`
Finds customers due for reminders based on booking history.

**User Story**: *As a system, I want to automatically identify customers whose service renewal window is approaching so we can send timely reminders.*

**Example**:
```python
from src.services.segmentation_service import SegmentationService

service = SegmentationService(db)
eligible = await service.identify_eligible_customers(
    cadence_days=21,  # 21 days since last booking
    send_window="9-18",  # Send between 9 AM - 6 PM
    batch_size=100
)
# Returns: [UUID("customer1"), UUID("customer2"), ...]
```

##### `SegmentationService.is_within_send_window(current_hour: int, send_window: str) -> bool`
Checks if current time is within allowed sending hours.

**User Story**: *As a customer, I want to receive reminders during business hours so they don't wake me up at night.*

**Example**:
```python
is_ok = service.is_within_send_window(
    current_hour=14,  # 2 PM
    send_window="9-18"
)
# Returns: True (14 is between 9 and 18)
```

##### `SegmentationService.get_customer_booking_history(customer_id: UUID, limit: int = 10) -> list[Booking]`
Retrieves recent booking history for context.

**User Story**: *As a system, I want to understand customer booking patterns so I can personalize reminder messages.*

**Example**:
```python
history = await service.get_customer_booking_history(customer_id, limit=5)
# Returns: [Booking(...), Booking(...), ...]
```

---

### 7. Safety Filter (`src/ai/safety.py`)

**Purpose**: Content moderation and tone analysis for AI-generated messages

#### Functions:

##### `SafetyFilter.check_message(message: str, message_type: str = "reminder", locale: str = "bn") -> tuple[bool, str | None]`
Validates message against safety rules.

**User Story**: *As a compliance officer, I want all AI-generated messages to be checked for inappropriate content before sending.*

**Example**:
```python
from src.ai.safety import get_safety_filter

filter = get_safety_filter()
is_safe, reason = filter.check_message(
    message="আপনার সার্ভিসের সময় হয়েছে!",
    message_type="reminder",
    locale="bn"
)
# Returns: (True, None) if safe
# Returns: (False, "Contains banned phrase: ...") if unsafe
```

##### `SafetyFilter.get_fallback_message(message_type: str = "reminder", locale: str = "bn") -> str`
Returns pre-approved fallback message.

**User Story**: *As a system, I want to use a safe, pre-approved message when AI generation fails so customers still receive reminders.*

**Example**:
```python
fallback = filter.get_fallback_message("reminder", "bn")
# Returns: "আপনার প্রিয় সার্ভিসের সময় হয়েছে। এখনই বুক করুন!"
```

---

### 8. SmartEngage Orchestrator (`src/ai/smartengage.py`)

**Purpose**: End-to-end orchestration of AI-powered Bengali reminders

#### Functions:

##### `SmartEngageOrchestrator.generate_and_send_reminder(customer_id: UUID, service_id: UUID, promo_code: str = None, ...) -> dict`
Complete workflow: segment → generate → filter → send → track.

**User Story**: *As a customer, I want to receive a personalized Bengali reminder about my upcoming service renewal with a convenient booking link.*

**Example**:
```python
from src.ai.smartengage import SmartEngageOrchestrator

orchestrator = SmartEngageOrchestrator(db)
result = await orchestrator.generate_and_send_reminder(
    customer_id=customer_id,
    service_id=service_id,
    promo_code="SAVE15",
    correlation_id=uuid4()
)
# Returns: {
#   "success": True,
#   "message_id": "uuid",
#   "correlation_id": "uuid"
# }
```

**Workflow Steps**:
1. Check consent (marketing opt-in)
2. Check frequency caps (not exceeded)
3. Load customer + service data
4. Get booking history for context
5. Generate AI message via OpenAI
6. Apply safety filter
7. Generate deep link with promo code
8. Send email notification
9. Create AIMessage record
10. Track metrics

##### `SmartEngageOrchestrator.generate_and_send_bulk_reminders(cadence_days: int = 21, ...) -> dict`
Bulk campaign processing for all eligible customers.

**User Story**: *As an operations manager, I want to automatically send reminders to all eligible customers at once so I don't have to process them individually.*

**Example**:
```python
result = await orchestrator.generate_and_send_bulk_reminders(
    cadence_days=21,
    send_window="9-18",
    batch_size=100,
    promo_code="HOLIDAY20"
)
# Returns: {
#   "total_eligible": 150,
#   "sent": 142,
#   "failed": 5,
#   "skipped": 3,
#   "duration_seconds": 45.2
# }
```

##### `SmartEngageOrchestrator._build_reminder_prompt(customer: User, service: Service, ...) -> str`
Constructs prompt for OpenAI with customer context.

**User Story**: *As a customer, I want reminders that mention my name and preferred service so they feel personal and relevant.*

**Example**:
```python
prompt = orchestrator._build_reminder_prompt(
    customer=customer,
    service=service,
    days_since_last=23,
    promo_code="SAVE20"
)
# Returns: "Generate a Bengali reminder for customer Fatima about..."
```

##### `SmartEngageOrchestrator._generate_message_with_openai(prompt: str, ...) -> str`
Calls OpenAI API to generate Bengali message.

**User Story**: *As a customer, I want reminders written in natural Bengali that sound friendly and professional.*

**Example**:
```python
message = await orchestrator._generate_message_with_openai(prompt)
# Returns: "প্রিয় ফাতিমা, আপনার ক্লিনিং সার্ভিসের সময় হয়েছে..."
```

---

### 9. Template Loader (`src/ai/template_loader.py`)

**Purpose**: Version-controlled prompt templates for AI agents

#### Functions:

##### `load_template(agent_type: str, locale: str = "bn", version: int = 1) -> str`
Loads prompt template from file.

**User Story**: *As a product manager, I want to update AI prompts without deploying code so I can iterate quickly on message quality.*

**Example**:
```python
from src.ai.template_loader import load_template

template = load_template("smartengage", locale="bn", version=1)
# Returns: "# SmartEngage Bengali Reminder Template v1\n\nনির্দেশনা:\n..."
```

##### `format_template(template: str, context: dict, promo_section: str = None) -> str`
Fills template with customer context.

**User Story**: *As a system, I want to insert customer-specific data into templates dynamically.*

**Example**:
```python
from src.ai.template_loader import format_template

prompt = format_template(
    template=template,
    context={
        "customer_name": "Fatima",
        "service_name_bn": "হোম ক্লিনিং",
        "days_since": 23
    },
    promo_section="প্রোমো কোড: SAVE20"
)
```

##### `get_template_version(agent_type: str, locale: str = "bn") -> int`
Gets latest template version available.

**User Story**: *As a system, I want to automatically use the latest approved template version.*

**Example**:
```python
from src.ai.template_loader import get_template_version

version = get_template_version("smartengage", "bn")
# Returns: 1 (latest version)
```

---

### 10. Campaign Runner (`src/jobs/campaign_runner.py`)

**Purpose**: Scheduled background job for automated campaigns

#### Functions:

##### `run_smartengage_campaign(db: Session, cadence_days: int = 21, ...) -> dict`
Executes SmartEngage campaign for eligible customers.

**User Story**: *As an operations manager, I want campaigns to run automatically every day so I don't have to trigger them manually.*

**Example**:
```python
from src.jobs.campaign_runner import run_smartengage_campaign

result = await run_smartengage_campaign(
    db=db,
    cadence_days=21,
    send_window="9-18",
    batch_size=100,
    correlation_id=uuid4()
)
# Returns: {
#   "status": "completed",
#   "sent": 142,
#   "failed": 3,
#   "duration_seconds": 45.2
# }
```

##### `trigger_campaign_manual(db: Session, dry_run: bool = False, preset: str = None, ...) -> dict`
Manually triggers campaign for testing.

**User Story**: *As an operations manager, I want to test campaigns in dry-run mode before sending to real customers.*

**Example**:
```python
from src.jobs.campaign_runner import trigger_campaign_manual

result = await trigger_campaign_manual(
    db=db,
    dry_run=True,  # No actual sends
    preset="aggressive",
    promo_code="TEST20"
)
# Returns: campaign results without sending emails
```

##### `register_campaign_jobs(scheduler: SchedulerManager)`
Registers recurring jobs with scheduler.

**User Story**: *As a system, I want to schedule daily campaigns at 9 AM UTC (3 PM Bangladesh time) automatically.*

**Example**:
```python
from src.jobs.campaign_runner import register_campaign_jobs
from src.jobs.scheduler import get_scheduler

scheduler = get_scheduler()
register_campaign_jobs(scheduler)
# Registers: SmartEngage campaign (daily 9 AM UTC)
```

---

### 11. Metrics Collector (`src/lib/metrics.py`)

**Purpose**: Prometheus-compatible observability metrics

#### Functions:

##### `MetricsCollector.increment_sends(agent_type: str, channel: str, message_type: str, status: str = "sent", amount: int = 1)`
Tracks message sends by agent, channel, and type.

**User Story**: *As an operations manager, I want to monitor how many messages are sent each day so I can track campaign volume.*

**Example**:
```python
from src.lib.metrics import get_metrics_collector

metrics = get_metrics_collector()
metrics.increment_sends(
    agent_type="smartengage",
    channel="EMAIL",
    message_type="REMINDER",
    status="sent"
)
```

##### `MetricsCollector.increment_opens(agent_type: str, channel: str, source: str = "unknown", amount: int = 1)`
Tracks notification opens.

**User Story**: *As a marketing manager, I want to measure email open rates so I can optimize subject lines.*

**Example**:
```python
metrics.increment_opens(
    agent_type="smartengage",
    channel="EMAIL",
    source="app"
)
```

##### `MetricsCollector.increment_clicks(agent_type: str, channel: str, source: str = "unknown", amount: int = 1)`
Tracks message clicks.

**User Story**: *As a product manager, I want to measure click-through rates so I can improve call-to-action messaging.*

**Example**:
```python
metrics.increment_clicks(
    agent_type="smartengage",
    channel="EMAIL",
    source="web"
)
```

##### `MetricsCollector.increment_conversions(agent_type: str, channel: str, conversion_type: str = "booking_created", amount: int = 1)`
Tracks conversions (bookings created).

**User Story**: *As a business analyst, I want to measure booking conversion rates from reminders so I can calculate ROI.*

**Example**:
```python
metrics.increment_conversions(
    agent_type="smartengage",
    channel="EMAIL",
    conversion_type="booking_created"
)
```

##### `MetricsCollector.export_prometheus() -> str`
Exports metrics in Prometheus text format.

**User Story**: *As a DevOps engineer, I want to scrape metrics into Prometheus so I can create dashboards and alerts.*

**Example**:
```python
prometheus_text = metrics.export_prometheus()
# Returns:
# # HELP ai_messages_sent_total Total number of AI-generated messages sent
# # TYPE ai_messages_sent_total counter
# ai_messages_sent_total{agent_type="smartengage",channel="EMAIL",...} 142
```

---

## User Stories & Features

### US1: SmartEngage Bengali Reminders ✅ COMPLETE

**Goal**: Deliver Bengali reminder before the renewal window with deep link; enforce consent/frequency caps; log outcomes.

#### Epic User Story
*As a customer who regularly books home services, I want to receive a personalized Bengali reminder when my service renewal window approaches, so I can easily rebook without having to remember the date myself.*

#### Feature Stories

1. **Reminder Eligibility** (T032: Segmentation)
   - *As a system, I want to identify customers whose last booking was ~21 days ago so I can send timely reminders.*
   - Files: `src/services/segmentation_service.py`

2. **Deep Link Generation** (T033: Deep Links)
   - *As a customer, I want to click a link and go directly to the booking page with my preferred service pre-selected.*
   - Files: `src/lib/deeplink.py`

3. **AI Message Generation** (T034: SmartEngage Orchestrator)
   - *As a customer, I want reminders written in natural Bengali that mention my name and service.*
   - Files: `src/ai/smartengage.py`, `src/ai/client.py`

4. **Automated Campaigns** (T035: Campaign Runner)
   - *As an operations manager, I want campaigns to run automatically every day at 3 PM Bangladesh time.*
   - Files: `src/jobs/campaign_runner.py`

5. **Manual & Bulk Sending** (T036, T038, T039: Admin APIs)
   - *As an admin, I want to manually send reminders to specific customers for testing or special cases.*
   - *As a marketing manager, I want to send bulk promos to all eligible customers at once.*
   - Files: `src/api/routes/internal_smartengage.py`, `src/api/routes/admin_smartengage.py`

6. **Consent & Frequency Control** (T023, T043: Consent + Config)
   - *As a customer, I want to control message frequency so I don't feel spammed.*
   - *As an operations manager, I want to configure frequency caps without code changes.*
   - Files: `src/lib/consent.py`, `src/lib/config_flags.py`

7. **Event Tracking** (T041: Events API)
   - *As a system, I want to track when customers open emails and click links so I can measure campaign effectiveness.*
   - Files: `src/api/routes/events.py`, `src/models/user_activity_events.py`

8. **Template Versioning** (T042: Templates)
   - *As a product manager, I want to update message templates without deploying code.*
   - Files: `src/ai/templates/smartengage_bn_v1.txt`, `src/ai/template_loader.py`

9. **Observability** (T044: Metrics)
   - *As a DevOps engineer, I want to monitor message volume, open rates, and conversions in Prometheus.*
   - Files: `src/lib/metrics.py`, `/metrics` endpoint

### US2: CoachNova Gentle Coaching 📋 PLANNED

**Goal**: Deliver empathetic Bengali coaching (text-first, voice optional) to workers with punctuality issues.

*Planned for future implementation (T045-T052)*

### US3: Manager Dashboard & Alerts 📋 PLANNED

**Goal**: Read-only dashboard for engagement and worker performance; burnout alerts.

*Planned for future implementation (T053-T058)*

---

## API Endpoints

### Public Endpoints

#### Authentication

**POST /auth/request-otp**
- **Purpose**: Request OTP code for login
- **User Story**: *As a user, I want to receive a login code via email.*
- **Request**: `{"email": "user@example.com", "user_type": "customer"}`
- **Response**: `{"status": "sent", "message": "OTP sent to email"}`

**POST /auth/verify-otp**
- **Purpose**: Verify OTP and receive JWT token
- **User Story**: *As a user, I want to enter my code and access my account.*
- **Request**: `{"email": "user@example.com", "code": "123456"}`
- **Response**: `{"access_token": "eyJhbGci...", "user": {...}}`

#### Services

**GET /services**
- **Purpose**: List available services
- **User Story**: *As a customer, I want to browse available services.*
- **Query Params**: `category`, `include_inactive`
- **Response**: `[{"id": "uuid", "name": "Home Cleaning", ...}]`

#### Events

**POST /events**
- **Purpose**: Track user interactions (opens, clicks, bookings)
- **User Story**: *As a system, I want to record when customers interact with messages.*
- **Auth**: JWT required
- **Request**: `{"event_type": "message_clicked", "source": "app", "metadata": {...}}`
- **Response**: `{"status": "accepted", "event_id": "uuid"}`

### Admin Endpoints

#### Manual Send

**POST /admin/smartengage/send-single**
- **Purpose**: Send reminder to specific customer
- **User Story**: *As an admin, I want to manually trigger a reminder for testing.*
- **Request**: 
  ```json
  {
    "customer_id": "uuid",
    "message_type": "reminder",
    "service_id": "uuid",
    "promo_code": "SAVE20",
    "ttl_hours": 48
  }
  ```
- **Response**: `{"success": true, "message_id": "uuid", ...}`

**POST /admin/smartengage/send-bulk**
- **Purpose**: Send bulk reminders with filters
- **User Story**: *As a marketing manager, I want to send promos to all eligible customers.*
- **Request**:
  ```json
  {
    "customer_ids": ["uuid1", "uuid2"],
    "booking_cadence_days": 21,
    "service_id": "uuid",
    "promo_code": "WEEKEND50",
    "batch_size": 100,
    "bypass_frequency_caps": false
  }
  ```
- **Response**: `{"total_eligible": 150, "sent": 142, "failed": 5, ...}`

### Internal Endpoints (Scheduled Jobs)

**POST /internal/ai/smartengage/run-segment**
- **Purpose**: Trigger scheduled campaign
- **User Story**: *As a scheduler, I want to run daily campaigns automatically.*
- **Request**:
  ```json
  {
    "cadence_days": 21,
    "send_window": "9-18",
    "batch_size": 100,
    "preset": "default",
    "promo_code": "DAILY15"
  }
  ```
- **Response**: `{"status": "started", "correlation_id": "uuid", ...}`

### Observability Endpoints

**GET /health**
- **Purpose**: Health check for load balancers
- **Response**: `{"status": "ok"}`

**GET /metrics**
- **Purpose**: Prometheus metrics scraping
- **User Story**: *As a DevOps engineer, I want to scrape metrics into monitoring systems.*
- **Response**: Prometheus text format
  ```
  # HELP ai_messages_sent_total Total messages sent
  # TYPE ai_messages_sent_total counter
  ai_messages_sent_total{agent_type="smartengage",channel="EMAIL"} 142
  ```

---

## Database Models

### Core Entities

#### User
- **Purpose**: Base user account (customers, workers, admins)
- **Key Fields**: `id`, `email`, `phone`, `name`, `type`, `consent`
- **Relationships**: → Customer, → Worker, → AIMessage

#### Customer
- **Purpose**: Customer-specific attributes
- **Key Fields**: `id`, `typical_services`, `last_booking_at`
- **Relationships**: → User, → Booking

#### Worker
- **Purpose**: Worker-specific attributes
- **Key Fields**: `id`, `skills`, `zones`, `ratings_avg`
- **Relationships**: → User, → Booking

#### Service
- **Purpose**: Service catalog
- **Key Fields**: `id`, `name`, `name_bn`, `category`, `base_price`, `duration_minutes`
- **Relationships**: → Booking

#### Booking
- **Purpose**: Service booking records
- **Key Fields**: `id`, `customer_id`, `worker_id`, `service_id`, `status`, `scheduled_at`, `finished_at`
- **Relationships**: → Customer, → Worker, → Service

### AI & Engagement

#### AIMessage
- **Purpose**: All AI-generated messages (reminders, coaching)
- **Key Fields**: `id`, `user_id`, `agent_type`, `channel`, `message_type`, `message_text`, `delivery_status`, `correlation_id`
- **User Story**: *As an analyst, I want to track all sent messages with their outcomes.*
- **Relationships**: → User, → AIMessageTemplate

#### AIMessageTemplate
- **Purpose**: Pre-approved message templates
- **Key Fields**: `id`, `agent_type`, `locale`, `template_type`, `template_text`
- **User Story**: *As a compliance officer, I want to audit approved message templates.*

#### UserActivityEvent
- **Purpose**: User interaction tracking (opens, clicks, conversions)
- **Key Fields**: `id`, `user_id`, `event_type`, `source`, `event_metadata`, `correlation_id`, `occurred_at`
- **User Story**: *As an analyst, I want to measure campaign attribution from message to booking.*
- **Relationships**: → User

### Background Jobs

#### Job
- **Purpose**: Distributed lock for scheduled jobs
- **Key Fields**: `id`, `job_name`, `status`, `locked_at`, `locked_by`
- **User Story**: *As a system, I want to ensure only one instance runs a job at a time.*

#### Campaign
- **Purpose**: Campaign execution records
- **Key Fields**: `id`, `campaign_type`, `status`, `eligible_count`, `sent_count`, `started_at`, `completed_at`
- **User Story**: *As an operations manager, I want to audit campaign execution history.*

---

## Services & Business Logic

### AuthService
- **Responsibilities**: OTP generation/verification, JWT issuance, user creation
- **Dependencies**: OTPProvider, JWT utilities, User model
- **Key Methods**: `request_otp()`, `verify_otp()`

### NotificationService
- **Responsibilities**: Multi-channel message sending (SMS, email, push)
- **Dependencies**: Twilio, SMTP, AIMessage model
- **Key Methods**: `send()`, `update_delivery_status()`

### SegmentationService
- **Responsibilities**: Customer eligibility for campaigns
- **Dependencies**: User, Customer, Booking, AIMessage models
- **Key Methods**: `identify_eligible_customers()`, `is_within_send_window()`

### MetricsCollector
- **Responsibilities**: Prometheus metrics collection
- **Dependencies**: None (singleton)
- **Key Methods**: `increment_sends()`, `increment_opens()`, `export_prometheus()`

---

## AI Agents

### SmartEngageOrchestrator
- **Purpose**: End-to-end Bengali reminder generation and delivery
- **AI Model**: OpenAI GPT-4o-mini
- **Language**: Bengali (bn)
- **Workflow**:
  1. Check consent + frequency caps
  2. Load customer + service data
  3. Build prompt with context
  4. Generate message via OpenAI
  5. Apply safety filter
  6. Generate deep link + promo
  7. Send email notification
  8. Track metrics

### CoachNova (Planned)
- **Purpose**: Empathetic worker coaching for performance issues
- **AI Model**: OpenAI GPT-4o-mini (text), Eleven Labs (voice)
- **Language**: Bengali (bn)
- **Planned**: T047-T052

---

## Background Jobs

### Campaign Runner
- **Schedule**: Daily at 9:00 AM UTC (3:00 PM Bangladesh time)
- **Job**: `run_smartengage_campaign`
- **Locking**: PostgreSQL advisory locks via `jobs` table
- **Parameters**:
  - `cadence_days`: 21 (default)
  - `send_window`: "9-18" (9 AM - 6 PM)
  - `batch_size`: 100
- **User Story**: *As a system, I want to automatically run campaigns every day without manual intervention.*

### Scheduler System
- **Technology**: APScheduler + PostgreSQL
- **Features**:
  - Distributed locking (prevents duplicate runs)
  - Cron and interval jobs
  - Event listeners (job start/finish/error)
  - Graceful shutdown
- **Files**: `src/jobs/scheduler.py`

---

## Configuration & Settings

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# OpenAI
OPENAI_API_KEY=sk-...

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

# OTP
OTP_PROVIDER=console  # or twilio
OTP_EXPIRATION_MINUTES=10

# Twilio (if using)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+1234567890

# App
APP_NAME=ShoktiAI Backend
BASE_URL=https://app.sheba.xyz
DEEP_LINK_BASE_URL=https://app.sheba.xyz/book

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@sheba.xyz
```

### Frequency Caps (Configurable)

```python
from src.lib.config_flags import FrequencyCaps, set_frequency_caps

# Default caps (aligned with research.md)
caps = FrequencyCaps(
    customer_daily_limit=1,
    customer_weekly_limit=2,
    customer_minimum_hours_between=24,
    worker_weekly_limit=1,
    worker_minimum_hours_between=72
)

# Update caps at runtime
set_frequency_caps(caps)
```

### Feature Flags (Configurable)

```python
from src.lib.config_flags import FeatureFlags, set_feature_flags

# Enable/disable features
flags = FeatureFlags(
    smartengage_enabled=True,
    coachnova_enabled=False,  # Not implemented yet
    ai_generation_enabled=True,
    safety_filter_enabled=True,
    deeplink_enabled=True
)

set_feature_flags(flags)
```

### Campaign Presets

- **default**: cadence=21d, batch=100, window=9-18h
- **aggressive**: cadence=14d, batch=200, window=8-20h
- **gentle**: cadence=28d, batch=50, window=10-17h
- **weekend**: cadence=21d, batch=150, window=10-16h

---

## Testing

### Test Coverage

- **Unit Tests**: 241 passing
- **Integration Tests**: 53 passing
- **Contract Tests**: 22 passing
- **Total**: 316 passing tests

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Individual functions and classes
   - Mocked dependencies
   - Fast execution (~0.5s)

2. **Integration Tests** (`tests/integration/`)
   - Multi-service workflows
   - Real database (test DB)
   - Slower execution (~2s)

3. **Contract Tests** (`tests/contract/`)
   - API endpoint validation
   - Request/response schemas
   - OpenAPI compliance

### Running Tests

```bash
# All tests
pytest tests/

# Specific suite
pytest tests/unit/test_smartengage_orchestrator.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Fast tests only (unit)
pytest tests/unit/ -v
```

---

## Metrics & Monitoring

### Prometheus Metrics

#### Message Metrics
- `ai_messages_sent_total`: Total messages sent
  - Labels: `agent_type`, `channel`, `message_type`, `status`
- `ai_messages_delivered_total`: Successfully delivered
  - Labels: `agent_type`, `channel`
- `ai_messages_failed_total`: Failed deliveries
  - Labels: `agent_type`, `channel`, `reason`

#### User Interaction Metrics
- `user_events_total`: User interactions
  - Labels: `event_type`, `agent_type`, `channel`, `source`
  - Events: `notification_opened`, `message_clicked`, `booking_created`, `deeplink_followed`

#### Opt-Out Metrics
- `opt_outs_total`: User opt-outs
  - Labels: `channel`, `reason`

### Accessing Metrics

```bash
# Prometheus scrape endpoint
curl http://localhost:8000/metrics

# Example output:
# HELP ai_messages_sent_total Total messages sent
# TYPE ai_messages_sent_total counter
ai_messages_sent_total{agent_type="smartengage",channel="EMAIL",message_type="REMINDER",status="sent"} 142
ai_messages_delivered_total{agent_type="smartengage",channel="EMAIL"} 138
user_events_total{event_type="message_clicked",agent_type="smartengage",channel="EMAIL",source="app"} 67
user_events_total{event_type="booking_created",agent_type="smartengage",channel="EMAIL"} 42
```

---

## Development Workflow

### Running Locally

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start development server
uvicorn src.api.app:app --reload --port 8000

# Server running at: http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current
```

### Code Quality

```bash
# Lint with ruff
ruff check .

# Format code
ruff format .

# Type checking (if using mypy)
mypy src/
```

---

## Deployment Checklist

### Pre-Production

- [ ] All tests passing (316/316)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Frequency caps configured per research.md
- [ ] Safety filter enabled
- [ ] Email templates approved
- [ ] Deep link URLs tested
- [ ] Metrics endpoint accessible
- [ ] Prometheus scraper configured
- [ ] Scheduler jobs registered

### Production

- [ ] SSL/TLS certificates installed
- [ ] CORS origins configured
- [ ] Rate limiting enabled (future)
- [ ] Backup strategy in place
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented
- [ ] Privacy policy compliance verified
- [ ] GDPR consent flows tested

---

## Future Enhancements

### Short Term (US2: CoachNova)
- Worker performance tracking
- Punctuality metrics
- Bengali coaching messages
- Voice message support (optional)
- Follow-up impact measurement

### Medium Term (US3: Dashboard)
- Operations dashboard
- Real-time metrics visualization
- Worker performance trends
- Burnout detection alerts
- Segment-level analytics

### Long Term
- Multi-language support (English, Hindi)
- SMS reminders (in addition to email)
- Push notifications
- WhatsApp integration
- A/B testing framework
- Machine learning for optimal send times
- Predictive churn modeling

---

## Support & Resources

### Documentation
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **OpenAPI Spec**: `specs/001-shoktiai-platform/contracts/openapi.yaml`
- **Research**: `specs/001-shoktiai-platform/research.md`
- **Data Model**: `specs/001-shoktiai-platform/data-model.md`

### Code Structure
- **Backend**: `backend/src/`
- **Tests**: `backend/tests/`
- **Migrations**: `backend/migrations/`
- **Specs**: `specs/001-shoktiai-platform/`

### Getting Help
- Review feature specs in `specs/001-shoktiai-platform/spec.md`
- Check implementation tasks in `specs/001-shoktiai-platform/tasks.md`
- Read quickstart guide in `specs/001-shoktiai-platform/quickstart.md`

---

## Appendix: Key Design Decisions

### Why JWT + OTP?
- Passwordless authentication reduces friction
- OTP via email is secure and accessible
- JWT enables stateless API authentication
- Suitable for customer-facing apps

### Why OpenAI GPT-4o-mini?
- Cost-effective for high-volume use
- Excellent Bengali language support
- Fast response times (<2s)
- Easy to prompt engineer

### Why PostgreSQL Advisory Locks?
- Prevents duplicate job execution in distributed systems
- No external dependencies (Redis, etc.)
- Built into PostgreSQL
- Reliable and battle-tested

### Why Prometheus Metrics?
- Industry standard for monitoring
- Rich ecosystem (Grafana, AlertManager)
- Pull-based scraping (no agent needed)
- Dimensional metrics with labels

### Why Email First (Not SMS)?
- Lower cost per message
- Rich formatting (HTML, links, images)
- No carrier restrictions
- Can include deep links

---

**Document Version**: 1.0.0  
**Last Updated**: November 5, 2025  
**Status**: US1 SmartEngage Complete ✅  
**Next Milestone**: US2 CoachNova (T045-T052)
