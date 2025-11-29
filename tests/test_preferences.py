from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app
from app.models.audit import AuditLog
from app.models.consent import (
    ConsentHistory,
    PurposeEnum,
    RegionEnum,
    StatusEnum,
    User,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def _create_user(email: str, region: RegionEnum = RegionEnum.EU) -> UUID:
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


def test_get_preferences_no_history_returns_revoked(client):
    user_id = _create_user("no-history@example.com", RegionEnum.CA)

    response = client.get(f"/consent/preferences/{user_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(user_id)
    assert data["region"] == RegionEnum.CA.value
    assert set(data["preferences"].keys()) == {purpose.value for purpose in PurposeEnum}
    assert all(status == StatusEnum.REVOKED.value for status in data["preferences"].values())


def test_update_single_preference_appends_history_and_audit_log(client):
    user_id = _create_user("single-update@example.com", RegionEnum.US)
    payload = {
        "user_id": str(user_id),
        "updates": {PurposeEnum.ANALYTICS.value: StatusEnum.GRANTED.value},
    }

    response = client.post("/consent/preferences/update", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["preferences"][PurposeEnum.ANALYTICS.value] == StatusEnum.GRANTED.value
    assert data["region"] == RegionEnum.US.value

    db = TestingSessionLocal()
    try:
        history = db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).all()
        assert len(history) == 1

        audit = db.query(AuditLog).filter(AuditLog.user_id == user_id).one()
        assert audit.action == "preferences.updated"
        assert audit.details["updates"][PurposeEnum.ANALYTICS.value] == StatusEnum.GRANTED.value
        assert audit.details["region"] == RegionEnum.US.value
    finally:
        db.close()


def test_update_multiple_preferences(client):
    user_id = _create_user("multi-update@example.com", RegionEnum.IN)
    payload = {
        "user_id": str(user_id),
        "updates": {
            PurposeEnum.ANALYTICS.value: StatusEnum.DENIED.value,
            PurposeEnum.MARKETING.value: StatusEnum.GRANTED.value,
        },
    }

    response = client.post("/consent/preferences/update", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["preferences"][PurposeEnum.ANALYTICS.value] == StatusEnum.DENIED.value
    assert data["preferences"][PurposeEnum.MARKETING.value] == StatusEnum.GRANTED.value

    db = TestingSessionLocal()
    try:
        history = db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).all()
        assert len(history) == 2
    finally:
        db.close()


def test_invalid_purpose_rejected(client):
    user_id = _create_user("invalid-purpose@example.com")
    payload = {"user_id": str(user_id), "updates": {"invalid": StatusEnum.GRANTED.value}}

    response = client.post("/consent/preferences/update", json=payload)
    assert response.status_code == 422

