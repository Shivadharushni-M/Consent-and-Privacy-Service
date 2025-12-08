from __future__ import annotations
import hashlib
from datetime import timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import AuditLog, ConsentHistory, RetentionEntityEnum, RetentionJob, RetentionJobStatusEnum, RetentionRule, RetentionSchedule, SubjectRequest, User
from app.models.consent import StatusEnum
from app.models.retention import RetentionEntityTypeEnum
from app.utils.helpers import get_utc_now


def _mark_expired_consents(db: Session) -> int:
    now = get_utc_now()
    expired_consents = db.query(ConsentHistory).filter(ConsentHistory.status == StatusEnum.GRANTED, ConsentHistory.valid_until.isnot(None), ConsentHistory.valid_until <= now).all()
    for consent in expired_consents:
        consent.status = StatusEnum.EXPIRED
    if expired_consents:
        db.commit()
    return len(expired_consents)


def _delete_stale_consents(db: Session, cutoff) -> int:
    return db.query(ConsentHistory).filter(ConsentHistory.timestamp < cutoff).delete(synchronize_session=False)


def _delete_stale_subject_requests(db: Session, cutoff) -> int:
    return db.query(SubjectRequest).filter(SubjectRequest.requested_at < cutoff).delete(synchronize_session=False)


def _anonymize_user_emails(db: Session, cutoff) -> int:
    stale_users = db.query(User).filter(User.updated_at < cutoff).all()
    now = get_utc_now()
    changed = 0
    for user in stale_users:
        if not user.email.startswith("anon-"):
            user.email = f"anon-{hashlib.sha256(f'{user.id}:{user.email}'.encode('utf-8')).hexdigest()[:12]}"
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
        
        expired_count = _mark_expired_consents(session)
        if expired_count > 0:
            session.add(AuditLog(user_id=None, actor_type="system", event_type="retention_run", action="consent_expiry_processed", details={"expired_count": expired_count}, event_time=now, created_at=now))
        rules = session.query(RetentionRule).all()
        if not rules:
            entity_map = {RetentionEntityEnum.CONSENT.value: RetentionEntityTypeEnum.CONSENT_RECORD.value, RetentionEntityEnum.AUDIT.value: RetentionEntityTypeEnum.AUDIT_LOG_ENTRY.value, RetentionEntityEnum.USER.value: RetentionEntityTypeEnum.CONSENT_RECORD.value}
            schedules = session.query(RetentionSchedule).filter(RetentionSchedule.active.is_(True)).all()
            rules = [type('RuleProxy', (), {'entity_type': type('Enum', (), {'value': entity_map.get(s.entity_type.value, RetentionEntityTypeEnum.CONSENT_RECORD.value)})(), 'retention_period_days': s.retention_days})() for s in schedules]
        results: List[Dict[str, object]] = []
        total_deleted = 0
        for rule in rules:
            cutoff = now - timedelta(days=rule.retention_period_days)
            entity_type_value = rule.entity_type.value if hasattr(rule.entity_type, 'value') else rule.entity_type if isinstance(rule.entity_type, str) else str(rule.entity_type)
            consent_types = {RetentionEntityTypeEnum.CONSENT_RECORD.value, "ConsentRecord", RetentionEntityEnum.CONSENT.value, "consent"}
            if entity_type_value in consent_types:
                deleted_count = _delete_stale_consents(session, cutoff) + _delete_stale_subject_requests(session, cutoff)
            elif entity_type_value in (RetentionEntityTypeEnum.RIGHTS_REQUEST.value, "RightsRequest"):
                deleted_count = _delete_stale_subject_requests(session, cutoff)
            elif entity_type_value in (RetentionEntityEnum.USER.value, "user"):
                deleted_count = _anonymize_user_emails(session, cutoff)
            else:
                deleted_count = 0
            details = {"rule": str(rule.entity_type), "deleted_count": deleted_count, "cutoff_date": cutoff.isoformat()}
            session.add(AuditLog(user_id=None, actor_type="system", event_type="retention_run", action="retention.cleanup", details=details, event_time=now, created_at=now))
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

