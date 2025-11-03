# Feature Specification: ShoktiAI Platform (SmartEngage + CoachNova)

**Feature Branch**: `[001-shoktiai-platform]`  
**Created**: 2025-11-03  
**Status**: Draft  
**Input**: User description captured from /speckit.specify (see `.specify/tmp/shoktiai-description.txt`)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Timely, Helpful Bengali Reminders Drive Bookings (Priority: P1)

Rahim is auto-segmented based on past behavior (e.g., books home cleaning every ~3 weeks). Before his typical renewal window, he receives a friendly Bengali reminder at his preferred time-of-day. He taps the link, reviews a pre-filled booking flow, optionally adds an add-on (e.g., fan cleaning), and confirms.

**Why this priority**: Direct revenue impact via increased repeat bookings and reduced user effort; validates SmartEngage core value (right message, right time, right tone).

**Independent Test**: Run a controlled cohort (treatment vs. control) where only SmartEngage reminders are active; measure booking conversion, time-to-book, and opt-out rate.

**Acceptance Scenarios**:

1. Given a customer with a detectable booking cadence, When the next window approaches, Then a Bengali reminder is delivered within the configured time window and includes a valid deep link to book.
2. Given a customer opens the reminder, When they proceed to booking, Then the flow is pre-populated with the relevant service and suggested add-ons and can be completed within 3 minutes.
3. Given a customer has opted out or exceeded frequency caps, When a reminder would otherwise be sent, Then no message is sent and a suppression reason is logged.

---

### User Story 2 - Gentle Coaching Improves Worker Punctuality and Ratings (Priority: P2)

Sadia receives empathetic Bengali coaching from CoachNova after analysis shows “arrives late sometimes.” She gets a short voice note and a 2-minute micro-lesson on time management. Over the next weeks, her punctuality improves and ratings rise.

**Why this priority**: Drives quality and retention on the supply side; validates CoachNova’s personalized, dignity-centered coaching loop.

**Independent Test**: Select a group of workers with punctuality deltas and deliver coaching; measure change in on-time arrival rate and average rating vs. a matched control group.

**Acceptance Scenarios**:

1. Given a worker with a punctuality issue detected over a defined window, When eligibility criteria are met, Then CoachNova delivers a Bengali coaching intervention (voice/text) within 24 hours, with a clear suggested action.
2. Given a worker receives coaching, When they complete at least 5 subsequent jobs, Then their on-time arrival rate improves by the target delta (see Success Criteria) or a follow-up intervention is scheduled.
3. Given a worker opts out of voice messages, When an intervention is due, Then a text-based alternative is delivered.

---

### User Story 3 - Manager Dashboard and Alerts Enable Data-Driven Operations (Priority: P3)

Nasir views a dashboard summarizing engagement and performance: customer engagement by segment (new, repeat, inactive), worker quality trends, satisfaction, and turnover risk. He receives burnout alerts for cohorts exceeding workload thresholds and can take action (e.g., pause offers, suggest breaks).

**Why this priority**: Operational leverage and governance; ensures the system is observable and humane at scale.

**Independent Test**: Enable read-only dashboard querying an events store; validate that specified metrics and alerts appear without running outreach/coaching features.

**Acceptance Scenarios**:

1. Given the platform is running for one week, When Nasir opens the dashboard, Then he can see engagement rate by segment, worker rating distributions, and satisfaction trends with filters.
2. Given a cohort exceeds burnout thresholds, When alerting conditions are met, Then Nasir receives a clear alert with cohort definition, driver(s), and recommended actions.

---

### Edge Cases

- Customer opted-out or lacks consent: messaging must be suppressed and logged with reason.
- Message fatigue: frequency caps prevent excessive outreach; stagger schedules to avoid clustering.
- Timing uncertainty: if preferred send-time is unknown, use a default window and learn from opens.
- Language fallback: if Bengali script rendering/voice is unavailable on device, provide clear-text fallback.
- Mis-segmentation: incorrect cadence inference must self-correct via feedback from dismissals/non-opens.
- Worker device constraints: if voice playback is unsupported or bandwidth is low, fall back to text.
- False burnout signals: short spikes shouldn't trigger; require sustained threshold breaches.
- Data gaps: if insufficient history, default to safe/no-op for automation and collect data first.

## Requirements *(mandatory)*

### Functional Requirements

- FR-001: System MUST generate and maintain customer segments (e.g., new, repeat, inactive) and individual behavior profiles (e.g., booking cadence, preferred open time).
- FR-002: System MUST schedule and send Bengali outreach messages within a configurable window aligned to user’s observed open times, with frequency caps and suppression rules (opt-out, recent contact, sensitive events).
- FR-003: System MUST include respectful, localized content templates and support personalization tokens (name, last service, next likely need) and deep links into booking flows.
- FR-004: System MUST track outreach lifecycle events end-to-end (scheduled, sent, delivered, opened, clicked, booked) with correlation identifiers to attribute outcomes.
- FR-005: System MUST infer likely add-ons (e.g., fan cleaning) based on past purchases and context and present as optional upsell in the booking flow.
- FR-006: System MUST compute worker performance signals (e.g., punctuality, ratings, completion rate) over rolling windows and determine coaching eligibility.
- FR-007: System MUST deliver Bengali coaching interventions (voice and/or text) with actionable guidance and micro-learning content and record acknowledgement/completion.
- FR-008: System MUST measure post-intervention impact (delta in punctuality/ratings over N jobs) and schedule follow-ups if targets aren’t met.
- FR-009: System MUST provide an operations dashboard with metrics: engagement by segment, booking conversion from outreach, worker performance trends, satisfaction/turnover indicators, and burnout cohort alerts.
- FR-010: System MUST implement opt-in/opt-out management, consent storage, and per-user frequency caps across all outreach and coaching communications.
- FR-011: System MUST provide transparent recognition options (e.g., loyalty bonus suggestions) for sustained performance, with a clear audit trail from trigger to award.
- FR-012: System MUST expose administrative controls to configure segments, send windows, suppression rules, thresholds, and success metrics without code changes.
- FR-013: System MUST localize all end-user content primarily in Bengali, with polite tone guidance and fallback to English where required.
- FR-014: System MUST protect dignity: no shaming language; all feedback framed positively with actionable next steps.
- FR-015: System MUST log errors, suppressions, and user feedback to continuously improve segmentation and coaching rules.

### Constitution Alignment (MANDATORY)

- Data handling and privacy: Personal data classes include customer identifiers, contact preferences, booking history, worker profiles, ratings, and coaching interactions. Consent MUST be recorded at the point of collection and honored for all communications. Retention follows purpose-limitation with periodic review; aggregated analytics may be retained longer after de-identification.
- Required SLOs for realtime interactions: For time-sensitive notifications and coaching, p95 end-to-end delivery/availability within 5 minutes; p99 within 15 minutes during normal operations. Booking flow from a deep link completes within 3 minutes for P95 users. Load/perf testing plans will validate these targets under expected peaks.
- Model/version contract: Where behavior inference or content generation is applied, define input schema (profile signals, recent interactions) and output schema (message intent, send window, recommended content) with versioned contracts and automated regression and safety checks (tone, respectfulness, harmful content filters) prior to delivery.
- Observability plan: Emit metrics for send volume, deliverability, opens, clicks, conversions, opt-outs, coaching sent, acknowledgements, post-intervention deltas, and burnout alerts. Include traceable correlation IDs from message → booking/coaching outcome. Structured logs for suppressions and errors. Alerts for SLO breaches and anomalous opt-out spikes.
- Release and versioning: Roll out in phases (P1 SmartEngage reminders → P2 CoachNova coaching → P3 dashboard). Support progressive exposure (e.g., percentage-based cohorts) with clear rollback to prior stable ruleset. Semantic version increments when changing externally observable behavior or data structures.

Missing or unclear items are blockers for Phase 1 sign-off where noted with [NEEDS CLARIFICATION].

### Key Entities *(include if feature involves data)*

- Customer Profile: attributes (id, segments, booking cadence, preferred contact time, consent state, language preferences).
- Engagement Message: campaign/context, content template, personalization tokens, send window, channel, frequency cap status, correlation id, delivery/open/click events.
- Booking Interaction: service selected, add-ons, time-to-complete, success/abandonment status.
- Worker Profile: attributes (id, skills, zones, schedule load, ratings history, punctuality metrics, opt-in preferences for coaching).
- Coaching Intervention: trigger reason, content modality (voice/text), lesson id, delivered timestamp, acknowledgement, completion, follow-up schedule.
- Performance Metric: rolling metrics (on-time %, average rating, job completion rate) with window definitions.
- Burnout Cohort: cohort definition, workload indicators (long shifts, consecutive days), alert state, recommended actions, acknowledgement.
- Recognition Award: type (e.g., loyalty bonus suggestion), trigger rationale, approval/issuance status, audit trail.

## Assumptions

- Primary user language is Bengali; respectful, dignified tone is non-negotiable.
- Initial channels are in-app and/or push/notification; SMS/voice may be considered if consented.
- Cadence inference starts with simple heuristics and can evolve without changing the contract to users.
- Manager dashboard is read-only in Phase 1; administrative controls cover configuration, not manual sends.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- SC-001: For eligible repeat customers, booking conversion from SmartEngage reminders improves by ≥ 20% vs. control within 60 days.
- SC-002: 90% of reminded customers who convert complete booking within 3 minutes from deep link.
- SC-003: Among coached workers with punctuality issues, on-time arrival improves by ≥ 15 percentage points within 4 weeks, and average rating increases to ≥ 4.5.
- SC-004: Customer opt-out rate for outreach remains ≤ 2% per month with ≥ 80% “useful” rating on message feedback prompts.
- SC-005: Burnout alerts achieve ≥ 70% precision when reviewed by operations, with corrective action initiated within 2 business days.
- SC-006: Manager dashboard adoption: ≥ 80% of operations managers use the dashboard weekly for the first 8 weeks.

### [NEEDS CLARIFICATION]

- CL-001: Outreach consent and frequency policy details [NEEDS CLARIFICATION: What default opt-in model and max weekly frequency should apply to customers and workers?]
- CL-002: Coaching modality priority [NEEDS CLARIFICATION: Should voice be default with text fallback, text-first, or user-selectable preference?]
- CL-003: Recognition budget governance [NEEDS CLARIFICATION: Who authorizes loyalty bonuses and what monthly caps/cohort rules apply?]
