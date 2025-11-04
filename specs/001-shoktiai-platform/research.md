# Research & Decisions: ShoktiAI Platform

Date: 2025-11-03  
Spec: `specs/001-shoktiai-platform/spec.md`

This document resolves planning unknowns and records key technology choices. For each item: Decision, Rationale, Alternatives considered.

## Clarifications from Spec

### CL-001: Outreach consent and frequency policy
- Decision: Explicit opt-in per channel (push, SMS, WhatsApp). Defaults: push enabled on app install with consent prompt; SMS/WhatsApp opt-in required. Frequency caps: customers ≤ 2 outreach messages/week; workers (coaching) ≤ 1/week, urgent alerts exempt with documented reason.
- Rationale: Respects user dignity and local expectations, reduces fatigue, aligns with low opt-out goals.
- Alternatives considered: Implicit opt-in (rejected for privacy), higher caps (risk fatigue), per-campaign caps only (harder governance).

### CL-002: Coaching modality priority
- Decision: Text-first with optional voice-note when worker has opted-in to voice and device supports it. Preference stored in profile; default is text.
- Rationale: Broader device compatibility, lower delivery cost; voice can be added incrementally.
- Alternatives considered: Voice-first (higher cost/friction), user-select every time (UI complexity on day 1).

### CL-003: Recognition budget governance
- Decision: Admin approval required for monetary/benefits awards. Monthly cap per cohort configured in admin settings; default total cap USD $500/month (or local equivalent). Auto-suggestions logged with audit trail; issuance requires approver role.
- Rationale: Budget control and auditability; avoids unbounded spend.
- Alternatives considered: Fully automated issuance (risk), ad-hoc manual grants (not auditable).

### CL-OTP-PROVIDER: OTP delivery provider
- Decision: Email SMTP (Gmail) for OTP delivery. Pluggable provider interface with "console" provider for dev/test. Rate-limit OTP requests and hash store codes server-side with short TTL (5 minutes).
- Rationale: Email is universally accessible in Bangladesh; lower cost than SMS; Gmail SMTP with app passwords is reliable and easy to configure.
- Alternatives considered: Twilio SMS (doesn't work in Bangladesh), Mocean SMS (connectivity issues), local SMS gateway (longer integration).

### CL-AI-MESSAGE-CHANNEL: AI message delivery channel
- Decision: Email as the primary channel for AI-generated messages (SmartEngage customer reminders and CoachNova worker coaching). SMS and WhatsApp remain as optional channels with provider adapters but email is the default and required channel.
- Rationale: Consistent with OTP provider decision; email works reliably in Bangladesh; beautiful HTML templates possible; lower cost; no SMS gateway dependencies.
- Alternatives considered: SMS-first (connectivity issues in Bangladesh), WhatsApp-first (requires business verification), push-only (requires app install).

### CL-ADMIN-MESSAGING: Admin-initiated AI messages
- Decision: Add admin API endpoints to allow managers/admins to manually trigger AI message generation and delivery to specific customers or workers. Requires admin authentication and logs all admin-initiated sends with admin user ID. Uses same AI generation pipeline (OpenAI + safety filters) but bypasses automated campaign triggers.
- Rationale: Enables human-in-the-loop intervention for special cases (VIP customers, urgent worker support); maintains safety guardrails; provides audit trail.
- Alternatives considered: Fully automated only (inflexible), manual message composition (bypasses AI safety), separate admin messaging system (duplication).

### CL-WA-PROVIDER: WhatsApp
- Decision: Defer for MVP. Design adapter interface; target Twilio WhatsApp or Meta Cloud API in Phase 3 if needed.
- Rationale: Avoid early complexity; push/SMS sufficient for MVP.
- Alternatives considered: Build immediately (added infra/approval work).

## Core Technology Choices

### Background jobs & scheduling
- Decision: APScheduler (in-process) for scheduled jobs (daily snapshots, campaign scans) plus a `jobs` table for bookkeeping and Postgres advisory locks to ensure single active runner. FastAPI BackgroundTasks for short, fire-and-forget tasks.
- Rationale: Minimal infra; meets MVP needs; simple to operate.
- Alternatives considered: Celery/RQ with Redis (more infra), OS cron (harder to deploy consistently), Kafka (overkill now).

### Notifications layer
- Decision: Abstraction `NotificationService` with adapters: `email_smtp` (primary), `sms_twilio`, `sms_mocean`, `push_stub` (initial), `whatsapp_tbd`. All sends logged to `ai_messages` and mirrored to `user_activity_events` with correlation ids. Email provider uses Gmail SMTP with SSL (port 465) and supports beautiful HTML templates with gradient styling.
- Rationale: Clear seams, easy to swap providers, unified logging. Email as primary channel works reliably in Bangladesh context.
- Alternatives: Hard-coded Twilio calls (tighter coupling), SMS-first (connectivity issues), third-party orchestration (cost/lock-in).

### Auth
- Decision: JWT (HS256) for API; phone+OTP login as primary, email+password optional later. Device/session tokens rotated; blacklist on logout if needed. Admin uses email+password + TOTP.
- Rationale: Simple and common for FastAPI; aligns with device apps.
- Alternatives: OAuth providers (not required initially).

### Data retention
- Decision: Events & ai_messages retained 12 months; booking/service data 7 years; prompts/outputs stored with PII removed and truncated context; configurable purge jobs.
- Rationale: Balance analytics value vs privacy/storage.
- Alternatives: Indefinite retention (privacy risk), aggressive deletion (hurts analytics).

### OpenAI usage
- Decision: Use GPT-4o/GPT-4o-mini for Bengali message/coaching generation with strict system prompts and max tokens limits; temperature tuned low for consistency. Safety filter: regex/tone checks and banned phrases list; manual review gate for new templates.
- Rationale: Quality in Bengali; control via prompts and filters.
- Alternatives: Local models (infra heavy), rule-only templates (lower personalization).

## Operational Practices
- Retries with exponential backoff for provider calls (httpx + tenacity). Circuit breakers on repeated failures.
- Idempotency keys for send operations to avoid duplicates.
- Metrics via Prometheus-compatible exporter or StatsD; logs structured (JSON) with correlation_id.
- Feature flags for campaigns/coaching; canary 10% rollout before full send.

## Consolidated Outcome
All planning clarifications resolved for Phase 1. The Constitution gates can PASS with the decisions above. Open items for future phases: WhatsApp adapter, budget policy refinement after pilot.
