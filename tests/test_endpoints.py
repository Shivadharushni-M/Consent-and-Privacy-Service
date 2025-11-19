import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import create_app
from app.db.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    Base.metadata.drop_all(bind=engine)

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_grant_consent_endpoint(client):
    response = client.post(
        "/consent/grant",
        json={
            "user_id": 1,
            "purpose": "analytics",
            "region": "GDPR",
            "policy_snapshot": {"version": "1.0"}
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == 1
    assert data["purpose"] == "analytics"
    assert data["status"] == "granted"
    assert data["region"] == "GDPR"

def test_revoke_consent_endpoint(client):
    response = client.post(
        "/consent/revoke",
        json={
            "user_id": 2,
            "purpose": "ads",
            "region": "CCPA"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == 2
    assert data["status"] == "revoked"

def test_get_history_endpoint(client):
    client.post("/consent/grant", json={"user_id": 3, "purpose": "analytics", "region": "GDPR"})
    client.post("/consent/grant", json={"user_id": 3, "purpose": "ads", "region": "GDPR"})
    
    response = client.get("/consent/history/3")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["user_id"] == 3 for item in data)

def test_invalid_user_id(client):
    response = client.post(
        "/consent/grant",
        json={
            "user_id": -1,
            "purpose": "analytics",
            "region": "GDPR"
        }
    )
    assert response.status_code == 422

def test_get_history_invalid_user(client):
    response = client.get("/consent/history/0")
    assert response.status_code == 400
    assert "Invalid user_id" in response.json()["detail"]

