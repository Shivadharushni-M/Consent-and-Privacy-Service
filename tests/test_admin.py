import uuid
from typing import Dict

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
    RequestStatusEnum,
    RequestTypeEnum,
    StatusEnum,
    SubjectRequest,
    User,
)
from app.utils.helpers import get_utc_now

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

    with TestClient(app, headers={"X-API-Key": settings.API_KEY}) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


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


def _snapshot(region: RegionEnum) -> Dict[str, str]:
    if region in {RegionEnum.EU, RegionEnum.INDIA}:
        policy = "gdpr"
    elif region == RegionEnum.US:
        policy = "ccpa"
    else:
        policy = "global"
    return {"region": region.value, "policy": policy}


def _seed_consent(user_id: uuid.UUID, purpose: PurposeEnum, status: StatusEnum, region: RegionEnum):
    db = TestingSessionLocal()
    try:
        record = ConsentHistory(
            user_id=user_id,
            purpose=purpose,
            status=status,
            region=region,
            policy_snapshot=_snapshot(region),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


def _seed_audit(user_id: uuid.UUID, action: str, purpose: PurposeEnum, region: RegionEnum):
    db = TestingSessionLocal()
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            details={
                "purpose": purpose.value,
                "region": region.value,
                "allowed": True,
                "reason": "policy",
            },
            policy_snapshot=_snapshot(region),
            created_at=get_utc_now(),
        )
        db.add(audit)
        db.commit()
    finally:
        db.close()


def _seed_subject_request(user_id: uuid.UUID, request_type: RequestTypeEnum):
    db = TestingSessionLocal()
    try:
        request = SubjectRequest(
            user_id=user_id,
            request_type=request_type,
            status=RequestStatusEnum.COMPLETED,
        )
        db.add(request)
        db.commit()
    finally:
        db.close()


def test_admin_users_filters_by_region(client: TestClient):
    eu_user = _create_user("admin-eu@example.com", RegionEnum.EU)
    _create_user("admin-us@example.com", RegionEnum.US)

    response = client.get("/admin/users", params={"region": RegionEnum.EU.value})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(eu_user)


def test_admin_consents_returns_history(client: TestClient):
    user_id = _create_user("history-admin@example.com", RegionEnum.EU)
    _seed_consent(user_id, PurposeEnum.ANALYTICS, StatusEnum.GRANTED, RegionEnum.EU)
    _seed_consent(user_id, PurposeEnum.MARKETING, StatusEnum.DENIED, RegionEnum.EU)

    response = client.get(f"/admin/consents/{user_id}")
    assert response.status_code == 200
    records = response.json()
    assert len(records) == 2
    assert records[0]["policy_snapshot"]["policy"] == "gdpr"


def test_admin_audit_filter_by_action(client: TestClient):
    user_id = _create_user("audit-admin@example.com", RegionEnum.US)
    _seed_audit(user_id, "decision", PurposeEnum.ANALYTICS, RegionEnum.US)
    _seed_audit(user_id, "event.processed", PurposeEnum.EMAIL, RegionEnum.US)

    response = client.get("/admin/audit", params={"action": "decision"})
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["action"] == "decision"
    assert logs[0]["policy_snapshot"]["policy"] == _snapshot(RegionEnum.US)["policy"]


def test_admin_subject_requests_returns_entries(client: TestClient):
    user_id = _create_user("subject-admin@example.com", RegionEnum.EU)
    _seed_subject_request(user_id, RequestTypeEnum.EXPORT)
    _seed_subject_request(user_id, RequestTypeEnum.DELETE)

    response = client.get("/admin/subject-requests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["user_id"] == str(user_id)

