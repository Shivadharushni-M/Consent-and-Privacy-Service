from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum
from app.services.preferences_service import get_latest_preferences
from app.utils.helpers import get_utc_now, validate_region

_GDPR_REGIONS = {RegionEnum.EU, RegionEnum.INDIA}
_SENSITIVE_KEYWORDS = {
    "analytics",
    "ads",
    "marketing",
    "location",
    "personalization",
    "email",
    "data_sharing",
}
_SENSITIVE_PURPOSES = frozenset(
    purpose
    for purpose in PurposeEnum
    if purpose.value in _SENSITIVE_KEYWORDS or purpose.name.lower() in _SENSITIVE_KEYWORDS
)


def _policy_allows(
    region: RegionEnum, purpose: PurposeEnum, current_status: Optional[StatusEnum]
) -> Tuple[bool, str]:
    if region in _GDPR_REGIONS:
        if purpose in _SENSITIVE_PURPOSES:
            if current_status == StatusEnum.GRANTED:
                return True, "gdpr_granted"
            return False, "gdpr_requires_grant"
        if current_status == StatusEnum.REVOKED:
            return False, "gdpr_revoked"
        if current_status == StatusEnum.DENIED:
            return False, "gdpr_denied"
        return True, "gdpr_default_allow"

    if region == RegionEnum.US:
        if current_status == StatusEnum.REVOKED:
            return False, "ccpa_revoked"
        if current_status == StatusEnum.DENIED:
            return False, "ccpa_denied"
        return True, "ccpa_default_allow"

    if current_status == StatusEnum.REVOKED:
        return False, "global_revoked"
    if current_status == StatusEnum.DENIED:
        return False, "global_denied"
    return True, "row_default_allow"


def _has_explicit_preference(db: Session, user_id: UUID, purpose: PurposeEnum) -> bool:
    return (
        db.query(ConsentHistory.id)
        .filter(ConsentHistory.user_id == user_id, ConsentHistory.purpose == purpose)
        .order_by(ConsentHistory.timestamp.desc())
        .first()
        is not None
    )


def decide(
    db: Session,
    user_id: UUID,
    purpose: PurposeEnum,
    *,
    fallback_region: Optional[RegionEnum] = None,
) -> Dict[str, Any]:
    stored_region, preferences = get_latest_preferences(db, user_id)
    region_candidate = stored_region or fallback_region or RegionEnum.ROW
    region = validate_region(region_candidate)

    current_status = preferences.get(purpose, StatusEnum.REVOKED)
    has_history = _has_explicit_preference(db, user_id, purpose)
    effective_status = current_status if has_history else None

    allowed, reason = _policy_allows(region, purpose, effective_status)

    audit = AuditLog(
        user_id=user_id,
        action="decision",
        details={
            "user_id": str(user_id),
            "purpose": purpose.value,
            "region": region.value,
            "allowed": allowed,
            "reason": reason,
        },
        created_at=get_utc_now(),
    )
    db.add(audit)
    db.commit()

    return {
        "user_id": user_id,
        "purpose": purpose,
        "region": region,
        "allowed": allowed,
        "reason": reason,
    }

