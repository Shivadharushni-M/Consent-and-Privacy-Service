from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import (
    AuditLog,
    ConsentHistory,
    RetentionEntityEnum,
    RetentionSchedule,
    SubjectRequest,
    User,
    VendorConsent,
)
from app.utils.helpers import get_utc_now


def _delete_stale_consents(db: Session, cutoff) -> int:
    consent_count = (
        db.query(ConsentHistory)
        .filter(ConsentHistory.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    vendor_count = (
        db.query(VendorConsent)
        .filter(VendorConsent.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    return consent_count + vendor_count


def _delete_stale_subject_requests(db: Session, cutoff) -> int:
    return (
        db.query(SubjectRequest)
        .filter(SubjectRequest.requested_at < cutoff)
        .delete(synchronize_session=False)
    )


def _anonymize_user_emails(db: Session, cutoff) -> int:
    stale_users: List[User] = (
        db.query(User).filter(User.updated_at < cutoff).all()
    )
    now = get_utc_now()
    changed = 0
    for user in stale_users:
        if user.email.startswith("anon-"):
            continue
        digest = hashlib.sha256(f"{user.id}:{user.email}".encode("utf-8")).hexdigest()[:12]
        user.email = f"anon-{digest}"
        user.updated_at = now
        changed += 1
    return changed


def run_retention_cleanup(db: Optional[Session] = None) -> Dict[str, object]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        now = get_utc_now()
        rules = (
            session.query(RetentionSchedule)
            .filter(RetentionSchedule.active.is_(True))
            .all()
        )
        results: List[Dict[str, object]] = []

        for rule in rules:
            cutoff = now - timedelta(days=rule.retention_days)
            deleted_count = 0

            if rule.entity_type == RetentionEntityEnum.CONSENT:
                deleted_count += _delete_stale_consents(session, cutoff)
                deleted_count += _delete_stale_subject_requests(session, cutoff)
            elif rule.entity_type == RetentionEntityEnum.USER:
                deleted_count = _anonymize_user_emails(session, cutoff)

            details = {
                "rule": rule.entity_type.value,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat(),
            }
            audit = AuditLog(
                user_id=None,
                action="retention.cleanup",
                details=details,
                created_at=get_utc_now(),
            )
            session.add(audit)
            results.append(details)

        session.commit()
        return {"processed": len(results), "results": results}
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()

