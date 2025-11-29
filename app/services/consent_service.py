import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum
from app.services import user_service
from app.utils.helpers import validate_region


def grant_consent(
    db: Session,
    user_id: uuid.UUID,
    purpose: PurposeEnum,
    region: RegionEnum,
) -> ConsentHistory:
    user = user_service.get_user(db, user_id)
    region_value = validate_region(region)

    consent = ConsentHistory(
        user_id=user.id,
        purpose=purpose,
        status=StatusEnum.GRANTED,
        region=region_value,
    )
    audit = AuditLog(
        user_id=user.id,
        action="CONSENT_GRANTED",
        details={"purpose": purpose.value, "region": region_value.value},
    )
    db.add_all([consent, audit])
    db.commit()
    db.refresh(consent)
    return consent


def revoke_consent(
    db: Session,
    user_id: uuid.UUID,
    purpose: PurposeEnum,
    region: RegionEnum,
) -> ConsentHistory:
    user = user_service.get_user(db, user_id)
    region_value = validate_region(region)

    consent = ConsentHistory(
        user_id=user.id,
        purpose=purpose,
        status=StatusEnum.REVOKED,
        region=region_value,
    )
    audit = AuditLog(
        user_id=user.id,
        action="CONSENT_REVOKED",
        details={"purpose": purpose.value, "region": region_value.value},
    )
    db.add_all([consent, audit])
    db.commit()
    db.refresh(consent)
    return consent


def get_history(db: Session, user_id: uuid.UUID) -> List[ConsentHistory]:
    user_service.get_user(db, user_id)
    return (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_id)
        .order_by(ConsentHistory.timestamp.desc())
        .all()
    )

