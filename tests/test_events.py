import uuid
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app
from app.models.audit import AuditLog
from app.models.consent import (
    ConsentHistory,
    EventNameEnum,
    PurposeEnum,
    RegionEnum,
    StatusEnum,
    User,
)
from app.services import event_service

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def _create_user(email: str, region: RegionEnum) -> uuid.UUID:
    db = TestingSessionLocal()
    try:
        user = User(email=email, region=region)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def _add_history(user_id: uuid.UUID, purpose: PurposeEnum, status: StatusEnum, region: RegionEnum) -> None:
    db = TestingSessionLocal()
    try:
        record = ConsentHistory(user_id=user_id, purpose=purpose, status=status, region=region)
        db.add(record)
        db.commit()
    finally:
        db.close()


def _event_audit_logs(user_id: uuid.UUID):
    db = TestingSessionLocal()
    try:
        return (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user_id, AuditLog.action == "event.processed")
            .all()
        )
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


def test_event_analytics_allowed_us(client: TestClient):
    user_id = _create_user("event-us@example.com", RegionEnum.US)

    response = client.post(
        "/events",
        json={
            "user_id": str(user_id),
            "event_name": EventNameEnum.PAGE_VIEW.value,
            "properties": {"path": "/"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["reason"] == "ccpa_default_allow"


def test_event_analytics_blocked_gdpr(client: TestClient):
    user_id = _create_user("event-eu@example.com", RegionEnum.EU)

    response = client.post(
        "/events",
        json={
            "user_id": str(user_id),
            "event_name": EventNameEnum.PAGE_VIEW.value,
            "properties": {"path": "/checkout"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["reason"] == "gdpr_requires_grant"


def test_event_email_handler_called(monkeypatch, client: TestClient):
    user_id = _create_user("event-email@example.com", RegionEnum.US)
    captured: Dict[str, object] = {"called": False}

    def fake_email_handler(event_name, properties):
        captured["called"] = True
        captured["event"] = event_name.value
        captured["properties"] = properties
        return {"provider": "email"}

    monkeypatch.setattr(event_service, "handle_email_event", fake_email_handler)

    response = client.post(
        "/events",
        json={
            "user_id": str(user_id),
            "event_name": EventNameEnum.NEWSLETTER_OPEN.value,
            "properties": {"campaign": "winter"},
        },
    )

    assert response.status_code == 200
    assert captured["called"] is True
    assert captured["event"] == EventNameEnum.NEWSLETTER_OPEN.value
    assert captured["properties"]["campaign"] == "winter"


def test_event_unknown_event_validation(client: TestClient):
    user_id = _create_user("event-unknown@example.com", RegionEnum.US)

    response = client.post(
        "/events",
        json={"user_id": str(user_id), "event_name": "unknown_event", "properties": {}},
    )

    assert response.status_code == 422


def test_location_event_blocked_when_revoked(client: TestClient):
    user_id = _create_user("event-location@example.com", RegionEnum.US)
    _add_history(user_id, PurposeEnum.LOCATION, StatusEnum.REVOKED, RegionEnum.US)

    response = client.post(
        "/events",
        json={
            "user_id": str(user_id),
            "event_name": EventNameEnum.LOCATION_PING.value,
            "properties": {"lat": 37.7749},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["reason"] == "ccpa_revoked"


def test_event_creates_audit_entry(client: TestClient):
    user_id = _create_user("event-audit@example.com", RegionEnum.US)

    response = client.post(
        "/events",
        json={
            "user_id": str(user_id),
            "event_name": EventNameEnum.SIGNUP.value,
            "properties": {"source": "referral"},
        },
    )

    assert response.status_code == 200
    logs = _event_audit_logs(user_id)
    assert len(logs) == 1
    assert logs[0].details["event_name"] == EventNameEnum.SIGNUP.value
    assert logs[0].details["allowed"] is True

