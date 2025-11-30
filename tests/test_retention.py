from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.jobs.retention import run_retention_cleanup
from app.models import (
    AuditLog,
    ConsentHistory,
    PurposeEnum,
    RegionEnum,
    RequestStatusEnum,
    RequestTypeEnum,
    RetentionEntityEnum,
    RetentionSchedule,
    StatusEnum,
    SubjectRequest,
    User,
)
from app.utils.helpers import get_utc_now

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_retention_cleanup_removes_expired_records(db: Session):
    user = User(email="retention@example.com", region=RegionEnum.EU)
    db.add(user)
    db.commit()
    db.refresh(user)

    schedule = RetentionSchedule(
        entity_type=RetentionEntityEnum.CONSENT,
        retention_days=30,
        active=True,
    )
    db.add(schedule)

    now = get_utc_now()
    expired_time = now - timedelta(days=35)
    recent_time = now - timedelta(days=5)

    expired_consent = ConsentHistory(
        user_id=user.id,
        purpose=PurposeEnum.ANALYTICS,
        status=StatusEnum.GRANTED,
        region=RegionEnum.EU,
        timestamp=expired_time,
        policy_snapshot={"region": "EU", "policy": "gdpr"},
    )
    recent_consent = ConsentHistory(
        user_id=user.id,
        purpose=PurposeEnum.MARKETING,
        status=StatusEnum.DENIED,
        region=RegionEnum.EU,
        timestamp=recent_time,
        policy_snapshot={"region": "EU", "policy": "gdpr"},
    )

    expired_request = SubjectRequest(
        user_id=user.id,
        request_type=RequestTypeEnum.DELETE,
        status=RequestStatusEnum.COMPLETED,
        requested_at=expired_time,
        completed_at=expired_time,
    )
    recent_request = SubjectRequest(
        user_id=user.id,
        request_type=RequestTypeEnum.EXPORT,
        status=RequestStatusEnum.PENDING,
        requested_at=recent_time,
    )

    db.add_all([expired_consent, recent_consent, expired_request, recent_request])
    db.commit()

    summary = run_retention_cleanup(db)

    assert summary["processed"] >= 1
    remaining_consents = db.query(ConsentHistory).all()
    assert len(remaining_consents) == 1
    assert remaining_consents[0].purpose == PurposeEnum.MARKETING

    remaining_requests = db.query(SubjectRequest).all()
    assert len(remaining_requests) == 1
    assert remaining_requests[0].request_type == RequestTypeEnum.EXPORT

    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "retention.cleanup")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert audit is not None
    assert audit.user_id is None
    assert audit.details["deleted_count"] == 2


def test_user_retention_anonymizes_email(db: Session):
    user = User(email="anonymize@example.com", region=RegionEnum.US)
    db.add(user)
    db.commit()
    db.refresh(user)

    schedule = RetentionSchedule(
        entity_type=RetentionEntityEnum.USER,
        retention_days=60,
        active=True,
    )
    db.add(schedule)

    user.updated_at = get_utc_now() - timedelta(days=90)
    db.add(user)
    db.commit()

    run_retention_cleanup(db)
    db.refresh(user)

    assert user.email.startswith("anon-")

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.action == "retention.cleanup")
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    user_audit = next(
        (log for log in logs if log.details.get("rule") == RetentionEntityEnum.USER.value),
        None,
    )
    assert user_audit is not None
    assert user_audit.details["deleted_count"] >= 1
