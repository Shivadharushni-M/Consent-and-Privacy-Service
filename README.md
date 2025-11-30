# Consent & Privacy Preferences Service

Backend service for managing user consent and privacy preferences with GDPR, CCPA, and DPDP compliance.

## Features

- ✅ Consent CRUD operations (grant/revoke/history)
- ✅ Immutable audit logging
- ✅ Region-based decision engine
- ✅ Subject rights workflows (export/delete/rectify)
- ✅ Automated data retention jobs with APScheduler
- ✅ Policy snapshots for every consent & decision
- ✅ API key authentication for every protected endpoint
- ✅ Admin insights across users, consents, audits, and requests

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
API_KEY=change-me
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
- **POST** `/subject-requests` - Create export/delete/rectify requests
- **GET** `/subject-requests/{request_id}` - Process export/delete requests

### Compliance & Admin

- **GET** `/retention/run` - Trigger automated cleanup
- **GET** `/admin/users` - List users (filter by `region`)
- **GET** `/admin/consents/{user_id}` - View consent history snapshots
- **GET** `/admin/audit` - Inspect audit logs (`action`, `purpose`, `region`)
- **GET** `/admin/subject-requests` - Review subject rights queue

> All endpoints except `/`, `/health`, and `/region` require `X-API-Key`.

### Health

- **GET** `/` - Service info
- **GET** `/health` - Health check

## Usage Examples

### Grant Consent

```bash
curl -X POST "http://localhost:8000/consent/grant" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "purpose": "analytics",
    "region": "GDPR"
  }'
```

### Revoke Consent

```bash
curl -X POST "http://localhost:8000/consent/revoke" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 42,
    "purpose": "analytics",
    "region": "GDPR"
  }'
```

### Get History

```bash
curl "http://localhost:8000/consent/history/42" \
  -H "X-API-Key: $API_KEY"
```

## Testing

### Run All Tests

```bash
pytest -q
```

### Run Specific Test File

```bash
pytest tests/test_consent.py -q
pytest tests/test_endpoints.py -q
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

## Deploy to Render

### Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Consent & Privacy Service"

# Add your GitHub repository (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Click "New +" → "Web Service"**
3. **Connect your GitHub repository**
4. **Render will auto-detect `render.yaml`** and configure:
   - Web service
   - PostgreSQL database
   - Environment variables

### Step 3: Set Environment Variables

After deployment, go to **Environment** tab and add:

```
SECRET_KEY=<generate-with-openssl-rand-hex-32>
API_KEY=<generate-with-openssl-rand-hex-32>
DEBUG=False
```

**Generate keys:**
```bash
openssl rand -hex 32  # Use this for SECRET_KEY
openssl rand -hex 32  # Use this for API_KEY
```

### Step 4: Verify Deployment

```bash
# Check health
curl https://your-service-name.onrender.com/health

# Test API
curl https://your-service-name.onrender.com/api/v1/version
```

**Note**: `DATABASE_URL` is automatically set by Render if using `render.yaml`.

### Manual Deploy (Without render.yaml)

If you prefer manual setup:

1. **Create PostgreSQL Database**:
   - Render Dashboard → "New +" → "PostgreSQL"
   - Note the **Internal Database URL**

2. **Create Web Service**:
   - Build Command: `pip install -r requirements.txt && alembic upgrade head`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment Variables:
     - `DATABASE_URL` (from PostgreSQL)
     - `SECRET_KEY` (generate strong key)
     - `API_KEY` (generate strong key)
     - `DEBUG=False`

## Compliance

This service helps with:

- **GDPR** (EU) - Explicit consent, right to erasure
- **CCPA** (California) - Opt-out model
- **DPDP** (India) - Data processing consent
- **Audit Trails** - Immutable logs for compliance

## License

MIT
