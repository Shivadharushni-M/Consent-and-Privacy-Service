import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.models.consent import ConsentHistory
from app.models.audit import AuditLog
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

def test_grant_consent(db):
    consent = consent_service.grant_consent(
        db=db,
        user_id=1,
        purpose="analytics",
        region="GDPR",
        policy_snapshot={"version": "1.0"}
    )
    
    assert consent.user_id == 1
    assert consent.purpose == "analytics"
    assert consent.status == "granted"
    assert consent.region == "GDPR"
    
    audit_log = db.query(AuditLog).filter(AuditLog.user_id == 1).first()
    assert audit_log is not None
    assert audit_log.action == "grant"
    assert audit_log.purpose == "analytics"

def test_revoke_consent(db):
    consent = consent_service.revoke_consent(
        db=db,
        user_id=2,
        purpose="ads",
        region="CCPA",
        policy_snapshot={"version": "1.0"}
    )
    
    assert consent.user_id == 2
    assert consent.purpose == "ads"
    assert consent.status == "revoked"
    assert consent.region == "CCPA"
    
    audit_log = db.query(AuditLog).filter(AuditLog.user_id == 2).first()
    assert audit_log is not None
    assert audit_log.action == "revoke"

def test_get_history(db):
    consent_service.grant_consent(db, 3, "analytics", "GDPR")
    consent_service.grant_consent(db, 3, "ads", "GDPR")
    consent_service.revoke_consent(db, 3, "analytics", "GDPR")
    
    history = consent_service.get_history(db, 3)
    
    assert len(history) == 3
    assert history[0].status == "revoked"
    assert history[1].status == "granted"
    assert history[2].status == "granted"

def test_immutable_consent_history(db):
    consent = consent_service.grant_consent(db, 4, "email", "India")
    
    with pytest.raises(Exception):
        consent.status = "revoked"
        db.commit()

