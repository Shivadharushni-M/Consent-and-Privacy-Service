from sqlalchemy.orm import Session
from app.models.consent import ConsentHistory
from app.models.audit import AuditLog
from typing import List, Dict, Any, Optional, Union
import uuid

def _convert_user_id(user_id: Union[int, str, uuid.UUID]) -> uuid.UUID:
    """Convert user_id to UUID format."""
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
        # This ensures the same integer always maps to the same UUID
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard namespace
        return uuid.uuid5(namespace, str(user_id))
    else:
        raise ValueError(f"Invalid user_id type: {type(user_id)}")

def grant_consent(
    db: Session,
    user_id: Union[int, str, uuid.UUID],
    purpose: str,
    region: str,
    policy_snapshot: Optional[Dict[str, Any]] = None
) -> ConsentHistory:
    # Convert user_id to UUID
    user_uuid = _convert_user_id(user_id)
    
    consent = ConsentHistory(
        user_id=user_uuid,
        purpose=purpose,
        status="granted",
        region=region,
        policy_snapshot=policy_snapshot
    )
    db.add(consent)
    
    audit = AuditLog(user_id=user_uuid, action="grant")
    db.add(audit)
    
    db.commit()
    db.refresh(consent)
    return consent

def revoke_consent(
    db: Session,
    user_id: Union[int, str, uuid.UUID],
    purpose: str,
    region: str,
    policy_snapshot: Optional[Dict[str, Any]] = None
) -> ConsentHistory:
    # Convert user_id to UUID
    user_uuid = _convert_user_id(user_id)
    
    consent = ConsentHistory(
        user_id=user_uuid,
        purpose=purpose,
        status="revoked",
        region=region,
        policy_snapshot=policy_snapshot
    )
    db.add(consent)
    
    audit = AuditLog(user_id=user_uuid, action="revoke")
    db.add(audit)
    
    db.commit()
    db.refresh(consent)
    return consent

def get_history(db: Session, user_id: Union[int, str, uuid.UUID]) -> List[ConsentHistory]:
    # Convert user_id to UUID
    user_uuid = _convert_user_id(user_id)
    return db.query(ConsentHistory).filter(
        ConsentHistory.user_id == user_uuid
    ).order_by(ConsentHistory.timestamp.desc()).all()

