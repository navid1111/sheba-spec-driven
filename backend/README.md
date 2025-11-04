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

## Key Features

### Authentication
- **OTP-based login**: SMS-based one-time passwords for secure authentication
- **JWT tokens**: HS256-signed tokens with 24-hour expiry
- **User provisioning**: Automatic user creation on first login

### Middleware
- **CORS**: Configured for local development (localhost:3000, localhost:5173)
- **Correlation ID**: Automatic request tracking with `X-Correlation-ID` header
  - Accepts custom correlation IDs from clients
  - Generates UUID if not provided
  - Includes in all responses and logs
- **Global error handling**: Consistent JSON error responses
- **Request logging**: Structured JSON logs with correlation ID

### Available Endpoints
- `GET /health` - Health check
- `POST /auth/request-otp` - Request OTP code
- `POST /auth/verify-otp` - Verify OTP and get JWT token

## Manual Testing

### Test Auth Flow
```powershell
# Start the server
uvicorn src.api.app:app --reload

# In another terminal, run the manual test script
python manual_test_auth.py
```

### Test Middleware
```powershell
# With server running
python manual_test_middleware.py
```

### Using curl
```powershell
# Health check
curl http://localhost:8000/health

# Request OTP
curl -X POST http://localhost:8000/auth/request-otp `
  -H "Content-Type: application/json" `
  -d '{"phone_number": "+8801715914254", "user_type": "customer"}'

# Check server console for OTP code, then verify
curl -X POST http://localhost:8000/auth/verify-otp `
  -H "Content-Type: application/json" `
  -d '{"phone_number": "+8801715914254", "otp_code": "123456"}'

# Test correlation ID
curl -H "X-Correlation-ID: my-test-id" http://localhost:8000/health
```

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
