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
    RetentionJob,
    RetentionJobStatusEnum,
    RetentionRule,
    RetentionSchedule,
    SubjectRequest,
    User,
    VendorConsent,
)
from app.models.retention import RetentionEntityTypeEnum
from app.models.consent import StatusEnum
from app.utils.helpers import get_utc_now


def _mark_expired_consents(db: Session) -> int:
    """Mark consents as expired if valid_until has passed."""
    now = get_utc_now()
    expired_consents = (
        db.query(ConsentHistory)
        .filter(
            ConsentHistory.status == StatusEnum.GRANTED,
            ConsentHistory.valid_until.isnot(None),
            ConsentHistory.valid_until <= now,
        )
        .all()
    )
    
    count = 0
    for consent in expired_consents:
        consent.status = StatusEnum.EXPIRED
        count += 1
    
    if count > 0:
        db.commit()
    
    return count


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
    job = RetentionJob(status=RetentionJobStatusEnum.RUNNING)
    session.add(job)
    session.flush()
    
    try:
        now = get_utc_now()
        
        # Mark expired consents first
        expired_count = _mark_expired_consents(session)
        if expired_count > 0:
            audit = AuditLog(
                user_id=None,
                actor_type="system",
                event_type="retention_run",
                action="consent_expiry_processed",
                details={"expired_count": expired_count},
                event_time=now,
                created_at=now,
            )
            session.add(audit)
        
        # Use RetentionRule if available, fallback to RetentionSchedule
        rules = session.query(RetentionRule).all()
        if not rules:
            # Convert RetentionSchedule to RetentionRule format
            # Map old RetentionEntityEnum to new RetentionEntityTypeEnum
            schedule_rules = session.query(RetentionSchedule).filter(
                RetentionSchedule.active.is_(True)
            ).all()
            rules = []
            for r in schedule_rules:
                # Map old enum values to new enum values
                entity_type_mapping = {
                    RetentionEntityEnum.CONSENT.value: RetentionEntityTypeEnum.CONSENT_RECORD.value,
                    RetentionEntityEnum.AUDIT.value: RetentionEntityTypeEnum.AUDIT_LOG_ENTRY.value,
                    RetentionEntityEnum.USER.value: RetentionEntityTypeEnum.CONSENT_RECORD.value,  # User data handled via consents
                }
                mapped_entity_type = entity_type_mapping.get(
                    r.entity_type.value,
                    RetentionEntityTypeEnum.CONSENT_RECORD.value
                )
                # Create a rule-like object with the mapped entity type
                class RuleProxy:
                    def __init__(self, entity_type, retention_period_days):
                        self.entity_type = entity_type
                        self.retention_period_days = retention_period_days
                
                rules.append(RuleProxy(mapped_entity_type, r.retention_days))
        
        results: List[Dict[str, object]] = []
        total_deleted = 0

        for rule in rules:
            cutoff = now - timedelta(days=rule.retention_period_days)
            deleted_count = 0
            
            # Handle both RetentionEntityTypeEnum (new) and string values
            entity_type_value = rule.entity_type
            if hasattr(rule.entity_type, 'value'):
                entity_type_value = rule.entity_type.value
            elif isinstance(rule.entity_type, str):
                entity_type_value = rule.entity_type

            if entity_type_value == RetentionEntityTypeEnum.CONSENT_RECORD.value or entity_type_value == "ConsentRecord":
                deleted_count += _delete_stale_consents(session, cutoff)
                deleted_count += _delete_stale_subject_requests(session, cutoff)
            elif entity_type_value == RetentionEntityTypeEnum.AUDIT_LOG_ENTRY.value or entity_type_value == "AuditLogEntry":
                # Audit logs are immutable per spec, so we don't delete them
                # Instead, we could anonymize PII in details if needed
                pass
            elif entity_type_value == RetentionEntityTypeEnum.RIGHTS_REQUEST.value or entity_type_value == "RightsRequest":
                deleted_count += _delete_stale_subject_requests(session, cutoff)
            # Legacy support for old RetentionEntityEnum values
            elif entity_type_value == RetentionEntityEnum.CONSENT.value or entity_type_value == "consent":
                deleted_count += _delete_stale_consents(session, cutoff)
                deleted_count += _delete_stale_subject_requests(session, cutoff)
            elif entity_type_value == RetentionEntityEnum.USER.value or entity_type_value == "user":
                deleted_count = _anonymize_user_emails(session, cutoff)

            details = {
                "rule": str(rule.entity_type),
                "deleted_count": deleted_count,
                "cutoff_date": cutoff.isoformat(),
            }
            audit = AuditLog(
                user_id=None,
                actor_type="system",
                event_type="retention_run",
                action="retention.cleanup",
                details=details,
                event_time=now,
                created_at=now,
            )
            session.add(audit)
            results.append(details)
            total_deleted += deleted_count

        job.status = RetentionJobStatusEnum.COMPLETED
        job.finished_at = get_utc_now()
        job.deleted_records_count = total_deleted
        job.log = {"results": results}
        
        session.commit()
        return {"processed": len(results), "results": results, "job_id": str(job.id)}
    except Exception as e:
        session.rollback()
        job.status = RetentionJobStatusEnum.FAILED
        job.finished_at = get_utc_now()
        job.log = {"error": str(e)}
        session.commit()
        raise
    finally:
        if owns_session:
            session.close()

