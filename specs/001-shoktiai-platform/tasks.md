---

description: "Task list for ShoktiAI Platform — Setup + Navid (AI-heavy) + Sadman (simpler)"
---

# Tasks: ShoktiAI Platform (SmartEngage + CoachNova)

**Input**: Design documents from `/specs/001-shoktiai-platform/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

Notes:
- Tests are included selectively where they unlock independent verification for each story.
- Assignees: User Story phases specify Navid (AI-heavy) or Sadman (simpler).

## Format: `[ID] [P?] [Story] Description`

- [P]: Can run in parallel (different files, no dependencies)
- [Story]: US1, US2, US3 (from spec.md)
- Include exact file paths in descriptions

## Path Conventions

- Backend-only project per plan: `backend/src/`, tests in `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

Purpose: Minimal project initialization so the team can collaborate and run the app locally.

- [X] T001 Create backend skeleton directories in `backend/src/{api,models,services,ai,jobs,lib}` and `backend/tests/{unit,integration,contract}`
- [X] T002 Create `backend/requirements.txt` with stack from plan.md (FastAPI, SQLAlchemy 2.x, Alembic, psycopg2-binary, Pydantic v2, httpx, PyJWT, python-dotenv, OpenAI, APScheduler, tenacity, pytest, pytest-asyncio, factory_boy)
- [X] T003 [P] Add `.env.example` in `backend/.env.example` with keys: DATABASE_URL, OPENAI_API_KEY, JWT_SECRET, OTP_PROVIDER, TWILIO_* (from quickstart.md)
- [X] T004 [P] Scaffold FastAPI app with health route in `backend/src/api/app.py` (GET /health -> 200 {status:"ok"})
- [X] T005 [P] Configure settings with pydantic-settings in `backend/src/lib/settings.py` (loads .env)
- [X] T006 [P] Configure database engine/session helper in `backend/src/lib/db.py` (SQLAlchemy 2.x, async optional later)
- [X] T007 [P] Initialize Alembic in `backend/` and configure `alembic.ini` sqlalchemy.url to use env `DATABASE_URL`
- [X] T008 [P] Add structured logging helper in `backend/src/lib/logging.py` (JSON logger + correlation_id support)
- [X] T009 [P] Add OpenAI client stub in `backend/src/ai/client.py` (reads OPENAI_API_KEY; no calls yet)
- [X] T010 [P] Add test scaffolding: `backend/tests/integration/test_health.py` (assert /health 200) using httpx TestClient
- [X] T011 [P] Add `backend/pyproject.toml` or `ruff.toml` and `pytest.ini` minimal configs
- [X] T012 Add `backend/README.md` quickstart (activate venv, install, run uvicorn, env variables)

Checkpoint: App skeleton runs (uvicorn) and /health passes.

---

## Phase 2: Foundational (Blocking Prerequisites)

Purpose: Core infrastructure required for ANY story to start.
CRITICAL: Must complete before user stories.

- [ ] T013 Define base models per data-model in `backend/src/models/__init__.py` and individual files: users.py, workers.py, customers.py, services.py, bookings.py, reviews.py
- [ ] T014 Create engagement/event models: `backend/src/models/ai_message_templates.py`, `backend/src/models/ai_messages.py`, `backend/src/models/user_activity_events.py`
- [ ] T015 Create jobs/campaign models: `backend/src/models/jobs.py`, `backend/src/models/campaigns.py`
- [ ] T016 Generate and run Alembic migrations for all above in `backend/migrations/` (upgrade creates tables + indexes)
- [ ] T017 [P] Implement JWT utilities in `backend/src/lib/jwt.py` (HS256, exp, iat, sub)
- [ ] T018 [P] Implement OTP provider abstraction in `backend/src/services/otp_provider.py` with `console` and `twilio` adapters
- [ ] T019 [P] Implement AuthService in `backend/src/services/auth_service.py` (request_otp, verify_otp -> issues JWT)
- [ ] T020 [P] Implement auth routes per contract: `backend/src/api/routes/auth.py` -> POST /auth/request-otp, /auth/verify-otp
- [ ] T021 Wire API router and middleware (CORS, correlation_id) in `backend/src/api/app.py`
- [ ] T022 [P] NotificationService abstraction in `backend/src/services/notification_service.py` (sms_twilio, push_stub); all sends write `ai_messages`
- [ ] T023 [P] Implement consent & frequency cap checks in `backend/src/lib/consent.py` used by NotificationService
- [ ] T024 [P] OpenAI safety filter and guardrails in `backend/src/ai/safety.py` (banned phrases, tone checks; reject or fallback)
- [ ] T025 [P] Scheduler runner in `backend/src/jobs/scheduler.py` (APScheduler + Postgres advisory lock via jobs table)
- [ ] T026 [P] Seed initial `ai_message_templates` migration in `backend/migrations/versions/` (SmartEngage reminder v1, CoachNova v1)
- [ ] T027 [P] Implement basic Services API: `backend/src/api/routes/services.py` (GET /services) with listing stub
- [ ] T028 [P] Add error handler middleware in `backend/src/api/middleware/error_handler.py` (maps exceptions to JSON errors)
- [ ] T029 Add minimal contract tests: `backend/tests/contract/test_auth_and_services_contract.py` for /auth/* and /services

Checkpoint: Auth + DB + scheduler + notifications + OpenAI guardrails are in place. Stories can start.

---

## Phase 3: User Story 1 — SmartEngage Bengali Reminders (Priority: P1) — Assignee: Navid 🎯 MVP

Goal: Deliver Bengali reminder before the renewal window with deep link; enforce consent/frequency caps; log outcomes.
Independent Test: Cohort A/B where only SmartEngage runs; measure booking conversion, click-to-book time, opt-out rate.

### Tests (kept minimal but enabling independent verification)

- [ ] T030 [P] [US1] Contract test for internal trigger `POST /internal/ai/smartengage/run-segment` in `backend/tests/contract/test_smartengage_contract.py`
- [ ] T031 [P] [US1] Integration test: simulate eligible customer -> ai_message created and NotificationService called in `backend/tests/integration/test_smartengage_flow.py`

### Implementation

- [ ] T032 [P] [US1] Implement segmentation heuristics in `backend/src/services/segmentation_service.py` (booking cadence, preferred send window)
- [ ] T033 [P] [US1] Implement deep link generator in `backend/src/lib/deeplink.py` (creates time-limited token -> booking flow)
- [ ] T034 [P] [US1] Implement SmartEngage orchestrator in `backend/src/ai/smartengage.py` (build context -> OpenAI -> safety -> ai_messages row)
- [ ] T035 [US1] Implement campaign runner job in `backend/src/jobs/campaign_runner.py` (query eligible users, frequency caps, enqueue sends)
- [ ] T036 [US1] Implement internal route `backend/src/api/routes/internal_smartengage.py` -> POST /internal/ai/smartengage/run-segment (fire job)
- [ ] T037 [US1] Extend NotificationService to persist correlation_id and delivery events in `ai_messages`
- [ ] T038 [US1] Track user events endpoint `backend/src/api/routes/events.py` -> POST /events to capture opens/clicks (per contract)
- [ ] T039 [US1] Add Bengali templates and prompt versions in `backend/src/ai/templates/smartengage_bn_v1.txt` and reference in DB
- [ ] T040 [US1] Add frequency caps configuration in `backend/src/lib/config_flags.py` (from research.md caps)
- [ ] T041 [US1] Observability: add metrics counters (sends, opens, clicks, conversions) in `backend/src/lib/metrics.py`

Checkpoint: US1 independently testable via internal trigger + integration test; messages stored and (stub) delivered.

---

## Phase 4: User Story 2 — CoachNova Gentle Coaching (Priority: P2) — Assignee: Navid

Goal: Deliver empathetic Bengali coaching (text-first, voice optional) to workers with punctuality issues; measure impact.
Independent Test: Select workers with punctuality deltas; deliver coaching; measure change vs control.

### Tests

- [ ] T042 [P] [US2] Contract test for `POST /internal/ai/coachnova/run-for-worker/{worker_id}` in `backend/tests/contract/test_coachnova_contract.py`
- [ ] T043 [P] [US2] Integration test: worker with late arrivals -> coaching message created with actionable tip in `backend/tests/integration/test_coachnova_flow.py`

### Implementation

- [ ] T044 [P] [US2] Implement performance signals in `backend/src/services/performance_service.py` (late arrivals, ratings, workload)
- [ ] T045 [P] [US2] Implement CoachNova orchestrator in `backend/src/ai/coachnova.py` (text-first; optional voice stub)
- [ ] T046 [US2] Implement internal route `backend/src/api/routes/internal_coachnova.py` -> POST /internal/ai/coachnova/run-for-worker/{worker_id}
- [ ] T047 [US2] Implement follow-up impact measurement job in `backend/src/jobs/coach_followup.py` (delta after N jobs; schedule next)
- [ ] T048 [US2] Add Bengali coaching templates and prompt versions in `backend/src/ai/templates/coaching_bn_v1.txt`
- [ ] T049 [US2] Extend consent/frequency checks for worker coaching paths in `backend/src/lib/consent.py`

Checkpoint: US2 independently testable via internal trigger + integration test; coaching stored and (stub) delivered.

---

## Phase 5: User Story 3 — Manager Dashboard & Alerts (Priority: P3) — Assignee: Sadman

Goal: Read-only dashboard for engagement and worker performance; burnout alerts.
Independent Test: Query endpoints without running outreach/coaching; expected metrics appear.

### Tests

- [ ] T050 [P] [US3] Integration test for `/admin/metrics/overview` in `backend/tests/integration/test_admin_overview.py` (uses seeded data)

### Implementation

- [ ] T051 [P] [US3] Implement metrics queries in `backend/src/services/metrics_service.py` (engagement by segment, conversions, ratings trends)
- [ ] T052 [US3] Implement `/admin/metrics/overview` route in `backend/src/api/routes/admin_metrics.py`
- [ ] T053 [P] [US3] Implement worker listing filters `/admin/workers` in `backend/src/api/routes/admin_workers.py` (low_rating filter)
- [ ] T054 [US3] Implement burnout alert computation in `backend/src/services/alerting_service.py` and expose via `backend/src/api/routes/admin_alerts.py`
- [ ] T055 [US3] Seed snapshot job `backend/src/jobs/snapshot_daily.py` to populate `worker_performance_snapshots`

Checkpoint: US3 independently testable via read-only endpoints; seeded jobs produce dashboard data.

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T056 [P] Security hardening: rate limits on auth and AI endpoints in `backend/src/api/middleware/rate_limit.py`
- [ ] T057 [P] Documentation updates in `specs/001-shoktiai-platform/quickstart.md` (validated steps)
- [ ] T058 Code cleanup and refactoring passes
- [ ] T059 [P] Add additional unit tests in `backend/tests/unit/` for core services
- [ ] T060 [P] Load/perf test scripts for SLOs in `backend/tests/perf/`

---

## Dependencies & Execution Order

### Phase Dependencies
- Setup (Phase 1): none
- Foundational (Phase 2): depends on Setup; BLOCKS all user stories
- User Stories (Phases 3–5): depend on Foundational; can proceed in parallel after Phase 2
- Polish: after desired stories complete

### User Story Dependencies
- US1 (P1, Navid): independent after Phase 2
- US2 (P2, Navid): independent after Phase 2 (may reuse shared libs but testable standalone)
- US3 (P3, Sadman): independent after Phase 2

### Within Stories
- Tests (when present) before implementation; models → services → endpoints → jobs/integration; ensure story-level checkpoint before moving on.

---

## Parallel Execution Examples

### US1 (Navid)
- Parallel: T032, T033, T034 can proceed together; T035 depends on them. Tests T030–T031 can run in parallel.

### US2 (Navid)
- Parallel: T044, T045 can proceed together; T047 depends on them. Tests T042–T043 can run in parallel.

### US3 (Sadman)
- Parallel: T051 and T053 in parallel; T052 depends on T051; T054 depends on T055.

---

## Implementation Strategy

- MVP First: Complete Phases 1–2, then Phase 3 (US1 — Navid). Demo and validate metrics. 
- Incremental: Add Phase 4 (US2 — Navid), then Phase 5 (US3 — Sadman). 
- Safety: Use safety filters and frequency caps per research.md; observe SLOs.

