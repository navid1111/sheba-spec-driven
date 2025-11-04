# Quickstart: ShoktiAI Backend (Prototype)

This guide gets you running a FastAPI backend with Postgres (Neon), scheduled jobs, and OpenAI integration for SmartEngage and CoachNova.

## Prerequisites
- Python 3.11+
- Postgres database (Neon recommended). Get a DATABASE_URL.
- OpenAI API key (for AI message generation).
- Optional: Twilio account (SMS) for OTP and messaging.

## Project layout (planned)
```
backend/
  src/{api,models,services,ai,jobs,lib}
  tests/{unit,integration,contract}
```

## Environment variables (.env)
- DATABASE_URL=postgresql+psycopg2://user:pass@host/db
- OPENAI_API_KEY=sk-...
- JWT_SECRET=change-me
- OTP_PROVIDER=console|twilio
- TWILIO_ACCOUNT_SID=...
- TWILIO_AUTH_TOKEN=...
- TWILIO_FROM_NUMBER=...

## Setup (Windows PowerShell)

1) Create and activate a virtual environment
```powershell
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
```

2) Install dependencies (to be added later in backend/requirements.txt)
```powershell
pip install fastapi uvicorn[standard] sqlalchemy alembic psycopg2-binary pydantic-settings python-dotenv httpx pyjwt apscheduler tenacity openai pytest pytest-asyncio factory_boy
```

3) Initialize Alembic (once code scaffold is added)
```powershell
# In backend/ directory
alembic init migrations
# Configure alembic.ini sqlalchemy.url to use %DATABASE_URL%
```

4) Run the API server (placeholder until code is scaffolded)
```powershell
uvicorn backend.src.api.app:app --reload --port 8000
```

5) Scheduler (placeholder)
- A single process will run APScheduler jobs for daily worker snapshots and campaign dispatch.

## Data & Contracts
- Data model: see `data-model.md`.
- API contract: see `contracts/openapi.yaml`.

## Safety & Governance
- Respect consent and frequency caps; routes must enforce JWT auth and RBAC.
- All AI messages pass safety checks; fallbacks used when checks fail.

## Next steps
- Scaffold the `backend/` code according to plan.
- Add requirements.txt and pre-commit hooks (ruff/black optional).
- Wire metrics/logging and feature flags.
