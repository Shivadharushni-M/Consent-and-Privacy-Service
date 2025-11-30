from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
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

    with TestClient(app, headers={"X-API-Key": settings.API_KEY}) as test_client:
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
        assert history[0].policy_snapshot["region"] == RegionEnum.US.value

        audit = db.query(AuditLog).filter(AuditLog.user_id == user_id).one()
        assert audit.action == "preferences.updated"
        assert audit.details["updates"][PurposeEnum.ANALYTICS.value] == StatusEnum.GRANTED.value
        assert audit.details["region"] == RegionEnum.US.value
        assert audit.policy_snapshot["policy"] == "ccpa"
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


def test_update_analytics_and_email_preferences(client):
    user_id = _create_user("analytics-email@example.com", RegionEnum.UK)
    payload = {
        "user_id": str(user_id),
        "updates": {
            PurposeEnum.ANALYTICS.value: StatusEnum.GRANTED.value,
            PurposeEnum.EMAIL.value: StatusEnum.DENIED.value,
        },
    }

    response = client.post("/consent/preferences/update", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["preferences"][PurposeEnum.ANALYTICS.value] == StatusEnum.GRANTED.value
    assert data["preferences"][PurposeEnum.EMAIL.value] == StatusEnum.DENIED.value

    db = TestingSessionLocal()
    try:
        history = db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).all()
        assert len(history) == 2
        stored_purposes = {entry.purpose for entry in history}
        assert {PurposeEnum.ANALYTICS, PurposeEnum.EMAIL}.issubset(stored_purposes)
    finally:
        db.close()


def test_get_preferences_handles_expired_entries(client):
    user_id = _create_user("expired@example.com", RegionEnum.CA)
    now = datetime.now(timezone.utc)

    db = TestingSessionLocal()
    try:
        db.add_all(
            [
                ConsentHistory(
                    user_id=user_id,
                    purpose=PurposeEnum.ANALYTICS,
                    status=StatusEnum.GRANTED,
                    region=RegionEnum.CA,
                    timestamp=now,
                    expires_at=now + timedelta(days=1),
                ),
                ConsentHistory(
                    user_id=user_id,
                    purpose=PurposeEnum.EMAIL,
                    status=StatusEnum.GRANTED,
                    region=RegionEnum.CA,
                    timestamp=now,
                    expires_at=now - timedelta(days=1),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(f"/consent/preferences/{user_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["preferences"][PurposeEnum.ANALYTICS.value] == StatusEnum.GRANTED.value
    assert data["preferences"][PurposeEnum.EMAIL.value] == StatusEnum.REVOKED.value


def test_get_preferences_unknown_user_returns_404(client):
    random_id = uuid4()

    response = client.get(f"/consent/preferences/{random_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "user_not_found"


def test_invalid_purpose_rejected(client):
    user_id = _create_user("invalid-purpose@example.com")
    payload = {"user_id": str(user_id), "updates": {"invalid": StatusEnum.GRANTED.value}}

    response = client.post("/consent/preferences/update", json=payload)
    assert response.status_code == 422

