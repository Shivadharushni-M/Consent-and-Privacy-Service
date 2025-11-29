from typing import Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum, User
from app.services import user_service
from app.utils.helpers import get_utc_now, validate_region


PreferencesMap = Dict[PurposeEnum, StatusEnum]


def _default_preferences() -> PreferencesMap:
    return {purpose: StatusEnum.REVOKED for purpose in PurposeEnum}


def _coerce_purpose(value) -> PurposeEnum:
    if isinstance(value, PurposeEnum):
        return value
    try:
        return PurposeEnum(value)
    except ValueError as exc:
        raise ValueError("invalid_purpose") from exc


def _coerce_status(value) -> StatusEnum:
    if isinstance(value, StatusEnum):
        return value
    try:
        return StatusEnum(value)
    except ValueError as exc:
        raise ValueError("invalid_status") from exc


def _resolve_user(db: Session, user_id: UUID, user: Optional[User]) -> User:
    if user is not None:
        return user
    return user_service.get_user(db, user_id)


def get_latest_preferences(
    db: Session, user_id: UUID, *, user: Optional[User] = None
) -> Tuple[RegionEnum, PreferencesMap]:
    user_obj = _resolve_user(db, user_id, user)
    preferences = _default_preferences()
    seen = set()

    history = (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_id)
        .order_by(ConsentHistory.timestamp.desc())
        .all()
    )

    for record in history:
        if record.purpose in seen:
            continue
        preferences[record.purpose] = record.status
        seen.add(record.purpose)
        if len(seen) == len(PurposeEnum):
            break

    return user_obj.region, preferences


def update_preferences(
    db: Session, user_id: UUID, updates: Dict[PurposeEnum, StatusEnum]
) -> Tuple[RegionEnum, PreferencesMap]:
    if not updates:
        raise ValueError("no_updates")

    user_obj = user_service.get_user(db, user_id)
    region = validate_region(user_obj.region)

    new_entries = []
    audit_updates = {}
    for purpose_raw, status_raw in updates.items():
        purpose = _coerce_purpose(purpose_raw)
        status = _coerce_status(status_raw)
        new_entries.append(
            ConsentHistory(
                user_id=user_obj.id,
                purpose=purpose,
                status=status,
                region=region,
                timestamp=get_utc_now(),
            )
        )
        audit_updates[purpose.value] = status.value

    db.add_all(new_entries)

    audit = AuditLog(
        user_id=user_obj.id,
        action="preferences.updated",
        details={"user_id": str(user_obj.id), "region": region.value, "updates": audit_updates},
        created_at=get_utc_now(),
    )
    db.add(audit)
    db.commit()

    return get_latest_preferences(db, user_obj.id, user=user_obj)

