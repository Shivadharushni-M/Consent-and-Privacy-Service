from datetime import timezone
from typing import Dict, Optional, Tuple, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum, User
from app.services import user_service
from app.utils.helpers import build_policy_snapshot, get_audit_log_kwargs, get_utc_now, validate_region
from app.utils.security import Actor

PreferencesMap = Dict[PurposeEnum, StatusEnum]


def get_latest_preferences(db: Session, user_id: UUID) -> Tuple[RegionEnum, PreferencesMap]:
    user = user_service.get_user(db, user_id)
    preferences = {purpose: StatusEnum.REVOKED for purpose in PurposeEnum}
    seen = set()
    now = get_utc_now()
    for record in db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).order_by(ConsentHistory.timestamp.desc()).all():
        if record.purpose in seen:
            continue
        expires_at = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at and not record.expires_at.tzinfo else record.expires_at
        preferences[record.purpose] = StatusEnum.REVOKED if expires_at and expires_at < now else record.status
        seen.add(record.purpose)
        if len(seen) == len(PurposeEnum):
            break
    return user.region, preferences


def update_preferences(db: Session, user_id: UUID, updates: Dict[PurposeEnum, StatusEnum], actor: Optional[Union[Actor, User]] = None) -> Tuple[RegionEnum, PreferencesMap]:
    if not updates:
        raise ValueError("no_updates")
    user = user_service.get_user(db, user_id)
    region = validate_region(user.region)
    snapshot = build_policy_snapshot(region)
    now = get_utc_now()
    new_entries = [ConsentHistory(user_id=user.id, purpose=purpose, status=status, region=region, timestamp=now, policy_snapshot=snapshot) for purpose, status in updates.items()]
    audit_kwargs = get_audit_log_kwargs(actor, user_id=user.id)
    db.add_all(new_entries)
    db.add(AuditLog(action="preferences.updated", details={"user_id": str(user.id), "region": region.value, "updates": {p.value: s.value for p, s in updates.items()}}, created_at=now, policy_snapshot=snapshot, **audit_kwargs))
    db.commit()
    return get_latest_preferences(db, user.id)

