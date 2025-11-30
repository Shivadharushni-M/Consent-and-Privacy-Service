import uuid
from datetime import datetime
from typing import List, Optional, Union, Dict, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum
from app.services import user_service
from app.utils.helpers import build_policy_snapshot, validate_region


def _convert_user_id(user_id: Union[int, str, uuid.UUID]) -> uuid.UUID:
    """Convert user_id to UUID format - for backward compatibility."""
    if isinstance(user_id, uuid.UUID):
        return user_id
    elif isinstance(user_id, str):
        try:
            return uuid.UUID(user_id)
        except ValueError:
            # If string is not a valid UUID, treat as integer
            return uuid.UUID(int=int(user_id) if user_id.isdigit() else hash(user_id) % (2**128))
    elif isinstance(user_id, int):
        # Convert integer to UUID deterministically using a namespace
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        return uuid.uuid5(namespace, str(user_id))
    else:
        raise ValueError(f"Invalid user_id type: {type(user_id)}")


def grant_consent(
    db: Session,
    user_id: Union[uuid.UUID, int, str],
    purpose: Union[PurposeEnum, str],
    region: Union[RegionEnum, str],
    expires_at: Optional[datetime] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> ConsentHistory:
    """Grant consent - supports both new (with enums) and old (with strings) signatures"""
    # Convert user_id to UUID if needed
    if isinstance(user_id, (int, str)) and not isinstance(user_id, uuid.UUID):
        user_uuid = _convert_user_id(user_id)
    else:
        user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))

    # Get or create user
    try:
        user = user_service.get_user(db, user_uuid)
    except ValueError:
        # User doesn't exist, create a basic one for backward compatibility
        from app.models.consent import User
        user = User(id=user_uuid, email=f"user_{user_uuid}@example.com", region=RegionEnum.ROW)
        db.add(user)
        db.flush()

    # Convert purpose and region to enums if they're strings
    if isinstance(purpose, str):
        try:
            purpose_enum = PurposeEnum(purpose.lower())
        except ValueError:
            raise ValueError("invalid_purpose")
    else:
        purpose_enum = purpose

    if isinstance(region, str):
        region_enum = validate_region(region)
    else:
        region_enum = validate_region(region)

    # Build policy snapshot
    if policy_snapshot:
        snapshot = policy_snapshot
    else:
        snapshot = build_policy_snapshot(region_enum)

    consent = ConsentHistory(
        user_id=user.id,
        purpose=purpose_enum,
        status=StatusEnum.GRANTED,
        region=region_enum,
        expires_at=expires_at,
        policy_snapshot=snapshot,
    )
    
    # Create audit log - support both old and new AuditLog structure
    try:
        audit = AuditLog(
            user_id=user.id,
            action="CONSENT_GRANTED",
            details={"purpose": purpose_enum.value if hasattr(purpose_enum, 'value') else str(purpose_enum), "region": region_enum.value if hasattr(region_enum, 'value') else str(region_enum)},
            policy_snapshot=snapshot,
        )
    except Exception:
        # Fallback for old AuditLog structure
        audit = AuditLog(
            user_id=user.id,
            action="grant",
        )

    db.add_all([consent, audit])
    try:
        db.commit()
        db.refresh(consent)
        return consent
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("database_error") from exc
    except Exception as exc:
        db.rollback()
        error_msg = str(exc) if exc else "Unknown error"
        raise ValueError(f"Failed to grant consent: {error_msg}") from exc


def revoke_consent(
    db: Session,
    user_id: Union[uuid.UUID, int, str],
    purpose: Union[PurposeEnum, str],
    region: Union[RegionEnum, str],
    expires_at: Optional[datetime] = None,
    policy_snapshot: Optional[Dict[str, Any]] = None,
) -> ConsentHistory:
    """Revoke consent - supports both new (with enums) and old (with strings) signatures"""
    # Convert user_id to UUID if needed
    if isinstance(user_id, (int, str)) and not isinstance(user_id, uuid.UUID):
        user_uuid = _convert_user_id(user_id)
    else:
        user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))

    # Get user
    try:
        user = user_service.get_user(db, user_uuid)
    except ValueError:
        raise ValueError("user_not_found")

    # Convert purpose and region to enums if they're strings
    if isinstance(purpose, str):
        try:
            purpose_enum = PurposeEnum(purpose.lower())
        except ValueError:
            raise ValueError("invalid_purpose")
    else:
        purpose_enum = purpose

    if isinstance(region, str):
        region_enum = validate_region(region)
    else:
        region_enum = validate_region(region)

    # Build policy snapshot
    if policy_snapshot:
        snapshot = policy_snapshot
    else:
        snapshot = build_policy_snapshot(region_enum)

    consent = ConsentHistory(
        user_id=user.id,
        purpose=purpose_enum,
        status=StatusEnum.REVOKED,
        region=region_enum,
        expires_at=expires_at,
        policy_snapshot=snapshot,
    )
    
    # Create audit log - support both old and new AuditLog structure
    try:
        audit = AuditLog(
            user_id=user.id,
            action="CONSENT_REVOKED",
            details={"purpose": purpose_enum.value if hasattr(purpose_enum, 'value') else str(purpose_enum), "region": region_enum.value if hasattr(region_enum, 'value') else str(region_enum)},
            policy_snapshot=snapshot,
        )
    except Exception:
        # Fallback for old AuditLog structure
        audit = AuditLog(
            user_id=user.id,
            action="revoke",
        )

    db.add_all([consent, audit])
    try:
        db.commit()
        db.refresh(consent)
        return consent
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("database_error") from exc
    except Exception as exc:
        db.rollback()
        error_msg = str(exc) if exc else "Unknown error"
        raise ValueError(f"Failed to revoke consent: {error_msg}") from exc


def get_history(db: Session, user_id: Union[uuid.UUID, int, str]) -> List[ConsentHistory]:
    """Get consent history - supports both UUID and string/integer user_id for backward compatibility"""
    # Convert user_id to UUID if needed
    if isinstance(user_id, (int, str)) and not isinstance(user_id, uuid.UUID):
        user_uuid = _convert_user_id(user_id)
    else:
        user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))

    # Try to get user (for validation)
    try:
        user_service.get_user(db, user_uuid)
    except ValueError:
        # If user doesn't exist, still return empty list for backward compatibility
        return []
    
    return (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_uuid)
        .order_by(ConsentHistory.timestamp.desc())
        .all()
    )
