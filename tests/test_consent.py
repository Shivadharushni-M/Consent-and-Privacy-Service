import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.audit import AuditLog
from app.models.consent import (
    ConsentHistory,
    PurposeEnum,
    RegionEnum,
    StatusEnum,
    User,
)
from app.services import consent_service

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def user(db):
    new_user = User(email=f"user-{uuid.uuid4()}@example.com", region=RegionEnum.EU)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


def test_grant_consent(db, user):
    consent = consent_service.grant_consent(
        db=db,
        user_id=user.id,
        purpose=PurposeEnum.ANALYTICS,
        region=RegionEnum.EU,
    )

    assert consent.user_id == user.id
    assert consent.purpose == PurposeEnum.ANALYTICS
    assert consent.status == StatusEnum.GRANTED
    assert consent.region == RegionEnum.EU
    assert consent.policy_snapshot is not None
    assert consent.policy_snapshot["policy"] == "gdpr"
    assert consent.policy_snapshot["default"] == "deny"

    audit_log = db.query(AuditLog).filter(AuditLog.user_id == user.id).first()
    assert audit_log is not None
    assert audit_log.action == "CONSENT_GRANTED"
    assert audit_log.details["purpose"] == PurposeEnum.ANALYTICS.value
    assert audit_log.details["region"] == RegionEnum.EU.value
    assert audit_log.policy_snapshot["policy"] == "gdpr"


def test_revoke_consent(db, user):
    consent = consent_service.revoke_consent(
        db=db,
        user_id=user.id,
        purpose=PurposeEnum.MARKETING,
        region=RegionEnum.UK,
    )

    assert consent.status == StatusEnum.REVOKED
    assert consent.policy_snapshot["policy"] == "gdpr"

    audit_log = db.query(AuditLog).filter(AuditLog.user_id == user.id).first()
    assert audit_log is not None
    assert audit_log.action == "CONSENT_REVOKED"
    assert audit_log.details["purpose"] == PurposeEnum.MARKETING.value


def test_get_history(db, user):
    consent_service.grant_consent(db, user.id, PurposeEnum.ANALYTICS, RegionEnum.US)
    consent_service.grant_consent(db, user.id, PurposeEnum.DATA_SHARING, RegionEnum.US)
    consent_service.revoke_consent(db, user.id, PurposeEnum.ANALYTICS, RegionEnum.US)

    history = consent_service.get_history(db, user.id)

    assert len(history) == 3
    assert history[0].status == StatusEnum.REVOKED
    assert {record.purpose for record in history} == {
        PurposeEnum.ANALYTICS,
        PurposeEnum.DATA_SHARING,
    }


def test_consent_history_is_append_only(db, user):
    consent_service.grant_consent(db, user.id, PurposeEnum.PERSONALIZATION, RegionEnum.CA)
    consent_service.revoke_consent(db, user.id, PurposeEnum.PERSONALIZATION, RegionEnum.CA)

    entries = (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user.id)
        .order_by(ConsentHistory.timestamp.asc())
        .all()
    )
    assert len(entries) == 2
    assert entries[0].status == StatusEnum.GRANTED
    assert entries[1].status == StatusEnum.REVOKED


def test_invalid_region_rejected(db, user):
    with pytest.raises(ValueError):
        consent_service.grant_consent(
            db=db,
            user_id=user.id,
            purpose=PurposeEnum.ANALYTICS,
            region="MARS",  # not in RegionEnum
        )

