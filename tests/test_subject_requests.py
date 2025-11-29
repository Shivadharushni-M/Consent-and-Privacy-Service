import uuid
from typing import Iterable, Tuple

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
    RequestStatusEnum,
    RequestTypeEnum,
    StatusEnum,
    SubjectRequest,
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


def _create_user(email: str, region: RegionEnum = RegionEnum.EU):
    db = TestingSessionLocal()
    try:
        user = User(email=email, region=region)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def _seed_history(
    user_id,
    entries: Iterable[Tuple[PurposeEnum, StatusEnum, RegionEnum]],
):
    db = TestingSessionLocal()
    try:
        records = [
            ConsentHistory(user_id=user_id, purpose=purpose, status=status, region=region)
            for purpose, status, region in entries
        ]
        db.add_all(records)
        db.commit()
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


def test_create_export_request(client):
    user_id = _create_user("export-create@example.com", RegionEnum.US)

    response = client.post(
        "/subject-requests",
        json={"user_id": str(user_id), "request_type": RequestTypeEnum.EXPORT.value},
    )
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == RequestStatusEnum.PENDING.value
    assert data["request_type"] == RequestTypeEnum.EXPORT.value
    assert data["request_id"]

    db = TestingSessionLocal()
    try:
        record = db.get(SubjectRequest, uuid.UUID(data["request_id"]))
        assert record is not None
        assert record.status == RequestStatusEnum.PENDING
        audit = db.query(AuditLog).filter(AuditLog.user_id == user_id).one()
        assert audit.action == "subject.request.created"
        assert audit.details["request_type"] == RequestTypeEnum.EXPORT.value
    finally:
        db.close()


def test_process_export_request(client):
    user_id = _create_user("export-process@example.com", RegionEnum.IN)
    _seed_history(
        user_id,
        [
            (PurposeEnum.ANALYTICS, StatusEnum.GRANTED, RegionEnum.IN),
            (PurposeEnum.ANALYTICS, StatusEnum.REVOKED, RegionEnum.IN),
            (PurposeEnum.EMAIL, StatusEnum.GRANTED, RegionEnum.IN),
        ],
    )

    created = client.post(
        "/subject-requests",
        json={"user_id": str(user_id), "request_type": RequestTypeEnum.EXPORT.value},
    ).json()

    response = client.get(f"/subject-requests/{created['request_id']}")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(user_id)
    assert data["region"] == RegionEnum.IN.value
    assert data["preferences"][PurposeEnum.ANALYTICS.value] == StatusEnum.REVOKED.value
    assert data["preferences"][PurposeEnum.EMAIL.value] == StatusEnum.GRANTED.value
    assert len(data["history"]) == 3

    db = TestingSessionLocal()
    try:
        history_count = (
            db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).count()
        )
        assert history_count == 3
        request = db.get(SubjectRequest, uuid.UUID(created["request_id"]))
        assert request.status == RequestStatusEnum.COMPLETED
    finally:
        db.close()


def test_create_delete_request(client):
    user_id = _create_user("delete-create@example.com", RegionEnum.EU)

    response = client.post(
        "/subject-requests",
        json={"user_id": str(user_id), "request_type": RequestTypeEnum.DELETE.value},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == RequestStatusEnum.PENDING.value
    assert data["request_type"] == RequestTypeEnum.DELETE.value

    db = TestingSessionLocal()
    try:
        audit = db.query(AuditLog).filter(AuditLog.user_id == user_id).one()
        assert audit.action == "subject.request.created"
    finally:
        db.close()


def test_process_delete_request(client):
    user_id = _create_user("delete-process@example.com", RegionEnum.CA)
    _seed_history(
        user_id,
        [
            (PurposeEnum.MARKETING, StatusEnum.GRANTED, RegionEnum.CA),
            (PurposeEnum.EMAIL, StatusEnum.DENIED, RegionEnum.CA),
        ],
    )

    export_request = client.post(
        "/subject-requests",
        json={"user_id": str(user_id), "request_type": RequestTypeEnum.EXPORT.value},
    ).json()
    delete_request = client.post(
        "/subject-requests",
        json={"user_id": str(user_id), "request_type": RequestTypeEnum.DELETE.value},
    ).json()

    response = client.get(f"/subject-requests/{delete_request['request_id']}")
    assert response.status_code == 200
    assert response.json() == {"status": "completed"}

    db = TestingSessionLocal()
    try:
        history_count = (
            db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).count()
        )
        assert history_count == 0

        remaining_requests = (
            db.query(SubjectRequest).filter(SubjectRequest.user_id == user_id).all()
        )
        assert len(remaining_requests) == 1
        assert remaining_requests[0].id == uuid.UUID(delete_request["request_id"])
        assert remaining_requests[0].status == RequestStatusEnum.COMPLETED

        assert db.get(SubjectRequest, uuid.UUID(export_request["request_id"])) is None

        audit = (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user_id, AuditLog.action == "subject.request.deleted")
            .one()
        )
        assert audit.details["request_id"] == delete_request["request_id"]
    finally:
        db.close()


def test_get_nonexistent_request_returns_404(client):
    response = client.get(f"/subject-requests/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "request_not_found"


