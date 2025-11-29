import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app
from app.models.consent import PurposeEnum, RegionEnum, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def _create_user(email: str, region: RegionEnum = RegionEnum.EU) -> uuid.UUID:
    db = TestingSessionLocal()
    try:
        user = User(email=email, region=region)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
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
    user_id = _create_user("grant@example.com")
    response = client.post(
        "/consent/grant",
        json={
            "user_id": str(user_id),
            "purpose": PurposeEnum.ANALYTICS.value,
            "region": RegionEnum.EU.value,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["purpose"] == PurposeEnum.ANALYTICS.value
    assert data["status"] == "granted"
    assert data["region"] == RegionEnum.EU.value


def test_revoke_consent_endpoint(client):
    user_id = _create_user("revoke@example.com")
    response = client.post(
        "/consent/revoke",
        json={
            "user_id": str(user_id),
            "purpose": PurposeEnum.MARKETING.value,
            "region": RegionEnum.UK.value,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["status"] == "revoked"


def test_get_history_endpoint(client):
    user_id = _create_user("history@example.com")
    client.post(
        "/consent/grant",
        json={"user_id": str(user_id), "purpose": PurposeEnum.ANALYTICS.value, "region": RegionEnum.US.value},
    )
    client.post(
        "/consent/grant",
        json={"user_id": str(user_id), "purpose": PurposeEnum.DATA_SHARING.value, "region": RegionEnum.US.value},
    )

    response = client.get(f"/consent/history/{user_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(item["user_id"] == str(user_id) for item in data)


def test_invalid_user_id(client):
    response = client.post(
        "/consent/grant",
        json={
            "user_id": str(uuid.uuid4()),
            "purpose": PurposeEnum.ANALYTICS.value,
            "region": RegionEnum.SG.value,
        },
    )
    assert response.status_code == 404


def test_get_history_invalid_user(client):
    response = client.get(f"/consent/history/{uuid.uuid4()}")
    assert response.status_code == 404

