# Data Model: ShoktiAI Platform

Source: `specs/001-shoktiai-platform/spec.md`  
Status: Draft (Phase 1 complete)

## Entities & Relationships

Notation: PK ▣, FK ◇. Timestamps include `created_at`, `updated_at` unless noted.

### users
- ▣ id (uuid)
- phone (unique, nullable if email auth)
- email (unique, nullable)
- name
- type (enum: customer, worker, admin)
- city, area
- language_preference (default: bn)
- last_login_at (nullable)
- is_active (bool, default true)
- consent: JSONB per channel, e.g. { push: true, sms: false, whatsapp: false, updated_at }
- metadata: JSONB

Constraints:
- Either phone or email must be present.
- Unique (phone) where not null.

### workers
- ▣ id (uuid) ◇ users.id (1:1)
- skills (text[])
- years_experience (int)
- rating_avg (numeric(3,2))
- total_jobs_completed (int)
- preferred_areas (text[])
- work_hours (JSONB, e.g. { mon: ["09:00-18:00"], ... })
- is_active (bool)
- opt_in_voice (bool, default false)

### customers
- ▣ id (uuid) ◇ users.id (1:1)
- typical_services (text[])
- last_booking_at (timestamptz, nullable)

### services
- ▣ id (uuid)
- name
- category (enum: cleaning, beauty, electrical, other)
- description
- base_price (numeric(10,2))
- duration_minutes (int)
- active (bool)

### bookings
- ▣ id (uuid)
- ◇ customer_id → customers.id
- ◇ worker_id → workers.id (nullable until assignment)
- ◇ service_id → services.id
- status (enum: pending, confirmed, in_progress, completed, cancelled)
- scheduled_at (timestamptz)
- started_at (timestamptz, nullable)
- finished_at (timestamptz, nullable)
- total_price (numeric(10,2))
- payment_status (enum: pending, paid, failed, refunded)
- deep_link_token (uuid, short-lived)

Validation:
- started_at >= scheduled_at; finished_at >= started_at.
- Only pending→confirmed→in_progress→completed or →cancelled.

### reviews
- ▣ id (uuid)
- ◇ booking_id → bookings.id (unique)
- rating (int 1..5)
- comment (text, nullable)
- flags (text[]; derived like late, rude, friendly)

### user_activity_events
- ▣ id (uuid)
- ◇ user_id → users.id
- event_type (enum: app_open, booking_created, message_clicked, notification_opened, etc.)
- source (enum: push, sms, app, web)
- metadata (JSONB: {campaign_id, screen_name, device, ai_message_id, ...})
- occurred_at (timestamptz)
- correlation_id (uuid)

Indexes: (user_id, occurred_at desc), (event_type, occurred_at desc)

### worker_performance_snapshots
- ▣ id (uuid)
- ◇ worker_id → workers.id
- date (date)
- jobs_completed_last_7_days (int)
- avg_rating_last_30_days (numeric(3,2))
- late_arrivals_last_7_days (int)
- cancellations_by_worker (int)
- hours_worked_last_7_days (numeric(5,2))
- workload_score (int 0..100)
- burnout_score (int 0..100)

Unique: (worker_id, date)

### ai_message_templates
- ▣ id (uuid)
- agent_type (enum: smartengage, coachnova)
- trigger_type (text)
- description (text)
- system_prompt (text)
- example_user_context (JSONB)
- version (int)
- active (bool)

### ai_messages
- ▣ id (uuid)
- ◇ user_id → users.id (nullable)
- ◇ worker_id → workers.id (nullable)
- role (enum: customer, worker)
- agent_type (enum: smartengage, coachnova)
- channel (enum: sms, app_push, whatsapp, in_app)
- message_text (text)
- message_type (enum: reminder, coaching, burnout_check, upsell)
- sent_at (timestamptz, nullable)
- delivery_status (enum: pending, sent, delivered, failed)
- user_response (enum: clicked, replied, ignored, booked, acknowledged, null)
- template_id (uuid, nullable) → ai_message_templates.id
- correlation_id (uuid)
- locale (text, default 'bn')
- safety_checks (JSONB)
- model (text)  # e.g., gpt-4o-mini-2025-xx
- prompt_version (int)

### campaigns
- ▣ id (uuid)
- type (enum: smartengage, coachnova)
- status (enum: scheduled, running, completed, failed)
- run_at (timestamptz)
- filters (JSONB)
- stats (JSONB: {users_targeted, users_reached, conversions})
- feature_flag (text)  # for canary rollouts

### jobs (scheduler bookkeeping)
- ▣ id (uuid)
- type (enum: snapshot_daily, campaign_runner, notifier, other)
- scheduled_for (timestamptz)
- payload (JSONB)
- status (enum: pending, processing, done, failed)
- run_at (timestamptz, nullable)
- attempts (int)
- lock_key (bigint, nullable)  # used with pg_try_advisory_lock

### learning_resources
- ▣ id (uuid)
- topic (text)
- url (text)
- estimated_time_minutes (int)
- active (bool)

## Relationships Diagram (high-level)
- users 1—1 workers; users 1—1 customers
- customers 1—* bookings *—1 workers; bookings *—1 services
- bookings 1—1 reviews
- users 1—* user_activity_events
- workers 1—* worker_performance_snapshots
- users/workers 1—* ai_messages; ai_messages *—1 ai_message_templates
- campaigns 1—* ai_messages (via correlation_id/metadata)

## Validation & Rules
- Consent checks required before any outbound send; frequency caps enforced via query and cached counters.
- Booking state transitions enforced by DB constraint or business logic with audit trail.
- AI messages must pass safety_checks before send; if not, fall back to deterministic template.

## State Machines
- Booking: pending → confirmed → in_progress → completed; any → cancelled (guarded).
- Campaign: scheduled → running → completed/failed.

## Indices & Performance
- Hot paths: bookings by customer_id, worker_id; events by user_id and occurred_at; ai_messages by delivery_status.
- Use partial indexes for delivery_status=pending for notifier job.

