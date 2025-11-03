# Implementation Plan: ShoktiAI Platform (SmartEngage + CoachNova)

**Branch**: `[001-shoktiai-platform]` | **Date**: 2025-11-03 | **Spec**: `specs/001-shoktiai-platform/spec.md`
**Input**: Feature specification from `/specs/001-shoktiai-platform/spec.md`

## Summary

Build a FastAPI-based backend with a Postgres (Neon) data layer, an AI orchestration layer that calls OpenAI for Bengali message/coaching generation, and a lightweight jobs/messaging system using Postgres plus a scheduler for campaigns and daily snapshots. Deliver core CRUD/auth, event logging, analytics snapshots, and initial AI-driven SmartEngage reminders and CoachNova coaching with contracts and observability.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, httpx, PyJWT, python-dotenv, OpenAI SDK, APScheduler 3.x (scheduler), tenacity (retry), uvicorn  
**Storage**: PostgreSQL (Neon) for OLTP; tables for users, workers, customers, services, bookings, reviews, events, snapshots, ai_messages, templates, campaigns/jobs  
**Testing**: pytest, pytest-asyncio, httpx test client, factory-boy for fixtures  
**Target Platform**: Linux container (uvicorn) behind a reverse proxy; dev on Windows/macOS acceptable  
**Project Type**: Web backend (API-only)  
**Performance Goals**: API p95 < 200ms under nominal load; AI delivery p95 < 5 minutes end-to-end; daily snapshot job < 15 minutes for 100k workers  
**Constraints**: JWT auth; phone OTP primary (Bangladesh). Rate-limits on auth and AI endpoints. Strict consent/frequency caps.  
**Scale/Scope**: Phase 1 target: 10–50k monthly active customers, 1–5k workers; 10s RPS burst on read endpoints; campaigns up to 50k messages/day.

NEEDS CLARIFICATION:
- OTP delivery provider and fallback (e.g., Twilio vs local SMS) [CL-OTP-PROVIDER]
- Default consent model and max weekly frequency for customers/workers [from spec CL-001]
- Coaching modality priority (voice vs text vs user preference) [from spec CL-002]
- Recognition governance: approver(s), monthly caps, cohort rules [from spec CL-003]
- WhatsApp enablement timeline/provider (if any) [CL-WA-PROVIDER]

## Constitution Check

Gate status (pre-Phase 0): CONDITIONAL PASS — sections defined; marked clarifications to be resolved in research. Any unresolved items post-Phase 1 will FAIL the gate.

Security & Privacy:
- Data classes: PII (phone, email, name), behavioral data (events), booking history, worker performance, AI content/logs.
- Consent: opt-in/opt-out stored per channel with timestamp and source; suppression honored globally. [CL-001]
- Retention: raw prompts/responses trimmed of PII; events 12 months; ai_messages 12 months; bookings 7 years; de-identified aggregates retained longer.
- RBAC: roles customer/worker/admin; admin-only access to campaigns/metrics; least-privileged DB access.
- Secrets in env; encryption in transit; at-rest via Neon defaults; DSRs supported (delete/anonymize user data on request).

Real-time Reliability & Performance:
- SLOs: API p95/p99 200/400ms; outreach end-to-end p95/p99 5/15 minutes; booking deep link flow complete in ≤3 minutes p95.
- Degradation: if AI unavailable, use safe fallback templates; if scheduler down, defer sends; rate-limit auth/AI.
- Capacity: APScheduler + single runner with Postgres advisory locks; campaign batching and backoff; idempotent job processing.

Deterministic & Testable AI Behavior:
- Versioned prompts and template IDs; input/output JSON schemas; store model name/version; safety filters for tone/respectfulness.
- Contract tests for message/coach payload shape; seeded examples for regression; retries with circuit-breakers.

Observability & Error Transparency:
- Structured logs with correlation_id; traces for API calls and AI calls; metrics: send volume, delivery, opens, clicks, conversions, coaching impact; alerts for SLO breaches and opt-out spikes.

Versioning & Governance:
- OpenAPI v1.0.0; semantic versioning for API/contracts; feature flags for campaigns/coaching; canary cohorts; rollback by disabling campaign flags and reverting templates.

## Project Structure

### Documentation (this feature)

```text
specs/001-shoktiai-platform/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (clarifications resolved)
├── data-model.md        # Phase 1 output (entities, rules, state)
├── quickstart.md        # Phase 1 output (setup & run)
└── contracts/           # Phase 1 output (OpenAPI)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/            # FastAPI routers (customer, worker, admin, internal)
│   ├── models/         # SQLAlchemy models + Alembic migrations
│   ├── services/       # domain services (booking, segmentation, notifications)
│   ├── ai/             # orchestration (SmartEngage, CoachNova)
│   ├── jobs/           # APScheduler jobs + job runners
│   └── lib/            # utils (auth, db, config, observability)
└── tests/
    ├── unit/
    ├── integration/
    └── contract/
```

**Structure Decision**: API-only backend in `backend/` with clear separation between API, domain services, AI orchestration, and jobs. Tests mirrored by layer.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Scheduler in-process | Simple MVP scheduling needs | External queues add infra ops burden initially |

---

Re-evaluation (post-Phase 1 design): PASS — CL-001/002/003 and provider choices are resolved in `research.md`. Remaining WhatsApp enablement is explicitly deferred with adapter seam; does not affect Phase 1 gates.

