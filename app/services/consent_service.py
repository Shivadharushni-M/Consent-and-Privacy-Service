from sqlalchemy.orm import Session
from app.models.consent import ConsentHistory
from app.models.audit import AuditLog
from typing import List, Dict, Any, Optional

def grant_consent(
    db: Session,
    user_id: int,
    purpose: str,
    region: str,
    policy_snapshot: Optional[Dict[str, Any]] = None
) -> ConsentHistory:
    consent = ConsentHistory(
        user_id=user_id,
        purpose=purpose,
        status="granted",
        region=region,
        policy_snapshot=policy_snapshot
    )
    db.add(consent)
    
    audit = AuditLog(user_id=user_id, action="grant", purpose=purpose)
    db.add(audit)
    
    db.commit()
    db.refresh(consent)
    return consent

def revoke_consent(
    db: Session,
    user_id: int,
    purpose: str,
    region: str,
    policy_snapshot: Optional[Dict[str, Any]] = None
) -> ConsentHistory:
    consent = ConsentHistory(
        user_id=user_id,
        purpose=purpose,
        status="revoked",
        region=region,
        policy_snapshot=policy_snapshot
    )
    db.add(consent)
    
    audit = AuditLog(user_id=user_id, action="revoke", purpose=purpose)
    db.add(audit)
    
    db.commit()
    db.refresh(consent)
    return consent

def get_history(db: Session, user_id: int) -> List[ConsentHistory]:
    return db.query(ConsentHistory).filter(
        ConsentHistory.user_id == user_id
    ).order_by(ConsentHistory.timestamp.desc()).all()

