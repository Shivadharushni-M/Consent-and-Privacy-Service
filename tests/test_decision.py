import uuid
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import create_app
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum, User

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


def _add_history(
    user_id: uuid.UUID, purpose: PurposeEnum, status: StatusEnum, region: RegionEnum
) -> None:
    db = TestingSessionLocal()
    try:
        record = ConsentHistory(user_id=user_id, purpose=purpose, status=status, region=region)
        db.add(record)
        db.commit()
    finally:
        db.close()


def _fetch_audit_log(user_id: uuid.UUID) -> Tuple[int, str]:
    db = TestingSessionLocal()
    try:
        logs = db.query(AuditLog).filter(AuditLog.user_id == user_id).all()
        return len(logs), logs[-1].details["reason"] if logs else ""
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


def test_decision_gdpr_needs_explicit_grant(client: TestClient):
    user_id = _create_user("gdpr@example.com", RegionEnum.EU)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.ANALYTICS.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["reason"] == "gdpr_requires_grant"


def test_decision_us_default_allow(client: TestClient):
    user_id = _create_user("ccpa@example.com", RegionEnum.US)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.MARKETING.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["reason"] == "ccpa_default_allow"

    log_count, reason = _fetch_audit_log(user_id)
    assert log_count == 1
    assert reason == "ccpa_default_allow"


def test_decision_india_like_gdpr(client: TestClient):
    user_id = _create_user("india@example.com", RegionEnum.INDIA)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.DATA_SHARING.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["reason"] in {"gdpr_requires_grant", "gdpr_revoked"}


def test_decision_row_default_allow(client: TestClient):
    user_id = _create_user("row@example.com", RegionEnum.ROW)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.PERSONALIZATION.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["reason"] == "row_default_allow"


def test_decision_granted_overrides(client: TestClient):
    user_id = _create_user("grant@example.com", RegionEnum.EU)
    _add_history(user_id, PurposeEnum.ANALYTICS, StatusEnum.GRANTED, RegionEnum.EU)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.ANALYTICS.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is True
    assert body["reason"] == "gdpr_granted"


def test_decision_revoked_overrides(client: TestClient):
    user_id = _create_user("revoked@example.com", RegionEnum.US)
    _add_history(user_id, PurposeEnum.MARKETING, StatusEnum.REVOKED, RegionEnum.US)

    response = client.get(
        "/decision",
        params={"user_id": str(user_id), "purpose": PurposeEnum.MARKETING.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["allowed"] is False
    assert body["reason"] == "ccpa_revoked"


def test_invalid_purpose_422(client: TestClient):
    user_id = _create_user("invalid-purpose@example.com", RegionEnum.US)

    response = client.get("/decision", params={"user_id": str(user_id), "purpose": "invalid"})

    assert response.status_code == 422

