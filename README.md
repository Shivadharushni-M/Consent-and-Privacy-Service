# Consent & Privacy Preferences Service

Backend service for managing user consent and privacy preferences with GDPR, CCPA, and DPDP compliance.

## Features

- ✅ Consent CRUD operations (grant/revoke/history)
- ✅ Immutable audit logging
- ✅ Region-based decision engine
- ✅ Subject rights workflows (export/delete)
- ✅ Automated data retention jobs
- ✅ Policy snapshots for compliance

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - ORM with declarative models
- **Alembic** - Database migrations
- **PostgreSQL** - Primary database
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **itsdangerous** - Secure token generation

## Project Structure

```
app/
├── config.py              # Settings & environment config
├── main.py                # Application factory
├── db/database.py         # Database connection
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic schemas
├── routes/                # API endpoints
├── services/              # Business logic
└── utils/                 # Helper utilities

tests/
├── test_consent.py        # Service layer tests
└── test_endpoints.py      # API integration tests

alembic/
└── versions/              # Database migrations
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/consent_db
SECRET_KEY=your-secret-key-here
DEBUG=False
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### Consent Management

- **POST** `/consent/grant` - Grant user consent
- **POST** `/consent/revoke` - Revoke user consent
- **GET** `/consent/history/{user_id}` - Get consent history

### Health

- **GET** `/` - Service info
- **GET** `/health` - Health check

## Usage Examples

### Grant Consent

```bash
curl -X POST "http://localhost:8000/consent/grant" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "purpose": "analytics",
    "region": "GDPR",
    "policy_snapshot": {"version": "1.0"}
  }'
```

### Revoke Consent

```bash
curl -X POST "http://localhost:8000/consent/revoke" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "purpose": "analytics",
    "region": "GDPR"
  }'
```

### Get History

```bash
curl "http://localhost:8000/consent/history/42"
```

## Testing

### Run All Tests

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_consent.py -v
pytest tests/test_endpoints.py -v
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

## Development

### Create New Migration

```bash
alembic revision --autogenerate -m "description"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Use strong `SECRET_KEY` (generate with `openssl rand -hex 32`)
3. Configure production PostgreSQL database
4. Use a production ASGI server (gunicorn + uvicorn workers)

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Compliance

This service helps with:

- **GDPR** (EU) - Explicit consent, right to erasure
- **CCPA** (California) - Opt-out model
- **DPDP** (India) - Data processing consent
- **Audit Trails** - Immutable logs for compliance

## License

MIT
