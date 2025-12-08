from datetime import datetime
from typing import List, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum, User
from app.services import user_service
from app.utils.helpers import build_policy_snapshot, get_audit_log_kwargs, validate_region
from app.utils.security import Actor


def _create_consent(db: Session, user_id: UUID, purpose: PurposeEnum, region: RegionEnum, status: StatusEnum, action: str, expires_at: Optional[datetime] = None, actor: Optional[Union[Actor, User]] = None) -> ConsentHistory:
    user = user_service.get_user(db, user_id)
    region_value = validate_region(region)
    snapshot = build_policy_snapshot(region_value)
    consent = ConsentHistory(user_id=user.id, purpose=purpose, status=status, region=region_value, expires_at=expires_at, policy_snapshot=snapshot)
    audit = AuditLog(action=action, details={"purpose": purpose.value, "region": region_value.value}, policy_snapshot=snapshot, **get_audit_log_kwargs(actor, user_id=user.id))
    db.add_all([consent, audit])
    db.commit()
    db.refresh(consent)
    return consent


def grant_consent(db: Session, user_id: UUID, purpose: PurposeEnum, region: RegionEnum, expires_at: Optional[datetime] = None, actor: Optional[Union[Actor, User]] = None) -> ConsentHistory:
    return _create_consent(db, user_id, purpose, region, StatusEnum.GRANTED, "CONSENT_GRANTED", expires_at, actor)


def revoke_consent(db: Session, user_id: UUID, purpose: PurposeEnum, region: RegionEnum, expires_at: Optional[datetime] = None, actor: Optional[Union[Actor, User]] = None) -> ConsentHistory:
    return _create_consent(db, user_id, purpose, region, StatusEnum.REVOKED, "CONSENT_REVOKED", expires_at, actor)


def get_history(db: Session, user_id: UUID) -> List[ConsentHistory]:
    user_service.get_user(db, user_id)
    return db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).order_by(ConsentHistory.timestamp.desc()).all()
