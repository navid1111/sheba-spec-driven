# ShoktiAI Backend

FastAPI-based backend for the ShoktiAI Platform (SmartEngage + CoachNova).

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Web framework
- **SQLAlchemy 2.x** - ORM
- **Alembic** - Database migrations
- **PostgreSQL** (Neon) - Database
- **OpenAI** - AI message generation
- **APScheduler** - Background jobs
- **pytest** - Testing

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database (Neon recommended)
- OpenAI API key

## Quick Start

### 1. Clone and Navigate

```powershell
cd backend
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```powershell
cp .env.example .env
```

Required variables:
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key
- `JWT_SECRET` - Secret for JWT signing (change in production)
- `OTP_PROVIDER` - `console` for dev, `twilio` for production
- `TWILIO_*` - Twilio credentials (if using twilio provider)

### 5. Run Database Migrations

```powershell
alembic upgrade head
```

### 6. Start the Server

```powershell
uvicorn src.api.app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

Health check: `http://localhost:8000/health`

## Development

### Run Tests

```powershell
# All tests
pytest

# Specific test file
pytest tests/integration/test_health.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Code Quality

```powershell
# Check code style
ruff check .

# Format code
ruff format .
```

### Database Migrations

```powershell
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current
```

### Project Structure

```
backend/
├── src/
│   ├── api/          # FastAPI routes and app
│   ├── models/       # SQLAlchemy models
│   ├── services/     # Business logic
│   ├── ai/           # AI orchestration (SmartEngage, CoachNova)
│   ├── jobs/         # Background jobs
│   └── lib/          # Shared utilities (db, logging, settings)
├── tests/
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── contract/     # Contract tests
├── migrations/       # Alembic migrations
├── requirements.txt  # Python dependencies
├── pytest.ini        # Pytest configuration
└── pyproject.toml    # Ruff configuration
```

## API Documentation

Once the server is running:
- Interactive docs (Swagger): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` in `.env`
- Check network connectivity to database
- Ensure database exists and is accessible

### Import Errors

- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.11+)

### Test Failures

- Run from `backend/` directory
- Ensure database is accessible
- Check logs in test output

## Contributing

1. Create a feature branch
2. Make changes
3. Run tests: `pytest`
4. Check code style: `ruff check .`
5. Submit PR

## License

Proprietary - All rights reserved
