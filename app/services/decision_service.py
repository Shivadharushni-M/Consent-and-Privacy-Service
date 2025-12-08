from typing import Any, Dict, Optional, Union
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum, User
from app.services.preferences_service import get_latest_preferences
from app.utils.helpers import build_policy_snapshot, get_audit_log_kwargs, get_utc_now, validate_region
from app.utils.security import Actor

_GDPR_REGIONS = {RegionEnum.EU, RegionEnum.INDIA, RegionEnum.UK, RegionEnum.IN}
_LGDP_REGIONS = {RegionEnum.BR}
_SENSITIVE_KEYWORDS = {"analytics", "ads", "marketing", "location", "personalization", "email", "data_sharing"}
_SENSITIVE_PURPOSES = frozenset(purpose for purpose in PurposeEnum if purpose.value in _SENSITIVE_KEYWORDS or purpose.name.lower() in _SENSITIVE_KEYWORDS)


def _policy_allows(region: RegionEnum, purpose: PurposeEnum, current_status: Optional[StatusEnum]) -> tuple[bool, str]:
    is_sensitive = purpose in _SENSITIVE_PURPOSES
    denied_statuses = (StatusEnum.REVOKED, StatusEnum.DENIED)
    if region in _GDPR_REGIONS:
        return (True, "gdpr_granted") if is_sensitive and current_status == StatusEnum.GRANTED else (False, "gdpr_requires_grant") if is_sensitive else (False, f"gdpr_{current_status.value}") if current_status in denied_statuses else (True, "gdpr_default_allow")
    if region in _LGDP_REGIONS:
        return (True, "lgpd_granted") if is_sensitive and current_status == StatusEnum.GRANTED else (False, "lgpd_requires_grant") if is_sensitive else (False, f"lgpd_{current_status.value}") if current_status in denied_statuses else (True, "lgpd_default_allow")
    if region == RegionEnum.US:
        return (False, f"ccpa_{current_status.value}") if current_status in denied_statuses else (True, "ccpa_default_allow")
    return (False, f"global_{current_status.value}") if current_status in denied_statuses else (True, "row_default_allow")


def _has_explicit_preference(db: Session, user_id: UUID, purpose: PurposeEnum) -> bool:
    return db.query(ConsentHistory.id).filter(ConsentHistory.user_id == user_id, ConsentHistory.purpose == purpose).first() is not None


def _check_consent_expiry(db: Session, user_id: UUID, purpose: PurposeEnum) -> bool:
    latest = db.query(ConsentHistory).filter(ConsentHistory.user_id == user_id, ConsentHistory.purpose == purpose).order_by(ConsentHistory.timestamp.desc()).first()
    return bool(latest and latest.expires_at and latest.expires_at < get_utc_now())


def decide(db: Session, user_id: UUID, purpose: PurposeEnum, *, fallback_region: Optional[RegionEnum] = None, actor: Optional[Union[Actor, User]] = None) -> Dict[str, Any]:
    stored_region, preferences = get_latest_preferences(db, user_id)
    region = validate_region(stored_region or fallback_region or RegionEnum.ROW)
    now = get_utc_now()
    if _check_consent_expiry(db, user_id, purpose):
        allowed, reason = False, "consent_expired"
    else:
        current_status = preferences.get(purpose, StatusEnum.REVOKED)
        has_history = _has_explicit_preference(db, user_id, purpose)
        allowed, reason = _policy_allows(region, purpose, current_status if has_history else None)
    policy_snapshot = build_policy_snapshot(region)
    audit_kwargs = get_audit_log_kwargs(actor, user_id=user_id)
    db.add(AuditLog(action="decision", details={"user_id": str(user_id), "purpose": purpose.value, "region": region.value, "allowed": allowed, "reason": reason}, created_at=now, policy_snapshot=policy_snapshot, **audit_kwargs))
    db.commit()
    return {"user_id": user_id, "purpose": purpose, "region": region, "allowed": allowed, "reason": reason, "policy_snapshot": policy_snapshot}

