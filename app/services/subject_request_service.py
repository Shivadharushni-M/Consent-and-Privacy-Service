from typing import Dict
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog, EventTypeEnum
from app.models.consent import (
    ConsentHistory,
    RegionEnum,
    RequestStatusEnum,
    RequestTypeEnum,
    SubjectRequest,
)
from app.schemas.consent import ConsentResponse
from app.schemas.subject_requests import DataAccessResponse, DataExportResponse
from app.services import consent_service, preferences_service, user_service
from app.utils.helpers import get_utc_now, validate_region
from app.utils.security import generate_verification_token

SUPPORTED_TYPES = {RequestTypeEnum.EXPORT, RequestTypeEnum.DELETE, RequestTypeEnum.ACCESS}


def create_request(db: Session, user_id: UUID, request_type: RequestTypeEnum) -> SubjectRequest:
    if request_type not in SUPPORTED_TYPES:
        raise ValueError("unsupported_request_type")

    user = user_service.get_user(db, user_id)
    request = SubjectRequest(
        user_id=user.id,
        request_type=request_type,
        status=RequestStatusEnum.PENDING_VERIFICATION,
        requested_at=get_utc_now(),
        # Note: verification_token_id is set separately by the caller (rights_v1.py)
    )

    audit = AuditLog(
        user_id=user.id,
        action="subject.request.created",
        details={
            "user_id": str(user.id),
            "request_id": str(request.id),
            "request_type": request_type.value,
        },
        created_at=get_utc_now(),
    )
    db.add_all([request, audit])
    db.commit()
    db.refresh(request)
    return request


def process_export_request(db: Session, request: SubjectRequest) -> DataExportResponse:
    if request.request_type != RequestTypeEnum.EXPORT:
        raise ValueError("unsupported_request_type")

    region, preferences = preferences_service.get_latest_preferences(db, request.user_id)
    history_records = consent_service.get_history(db, request.user_id)
    preferences_payload: Dict[str, str] = {
        purpose.value: status.value for purpose, status in preferences.items()
    }
    history_payload = [ConsentResponse.model_validate(record) for record in history_records]

    # Gather audit logs related to subject
    from app.models.audit import AuditLog
    audit_logs = db.query(AuditLog).filter(
        (AuditLog.subject_id == request.user_id) | (AuditLog.user_id == request.user_id)
    ).order_by(AuditLog.event_time.desc()).all()
    
    audit_logs_payload = []
    for log in audit_logs:
        audit_logs_payload.append({
            "id": str(log.id),
            "event_type": log.event_type,
            "action": log.action,
            "event_time": log.event_time.isoformat() if log.event_time else None,
            "details": log.details,
            "policy_snapshot": log.policy_snapshot,
        })

    # Gather unique policy snapshots from consent history and audit logs
    policy_snapshot_ids = set()
    for record in history_records:
        if record.policy_version_id:
            policy_snapshot_ids.add(record.policy_version_id)
    
    for log in audit_logs:
        if log.policy_snapshot and log.policy_snapshot.get("policy_version_id"):
            try:
                from uuid import UUID
                policy_snapshot_ids.add(UUID(log.policy_snapshot["policy_version_id"]))
            except (ValueError, TypeError):
                pass
    
    # Fetch policy versions
    from app.models.policy import PolicyVersion
    policy_snapshots_payload = []
    for pv_id in policy_snapshot_ids:
        pv = db.get(PolicyVersion, pv_id)
        if pv:
            policy_snapshots_payload.append({
                "id": str(pv.id),
                "policy_id": str(pv.policy_id),
                "version_number": pv.version_number,
                "effective_from": pv.effective_from.isoformat() if pv.effective_from else None,
                "effective_to": pv.effective_to.isoformat() if pv.effective_to else None,
                "matrix": pv.matrix,
                "created_at": pv.created_at.isoformat() if pv.created_at else None,
            })

    # Generate export data and store location (simplified - in production would write to storage)
    export_data = DataExportResponse(
        user_id=request.user_id,
        region=region,
        preferences=preferences_payload,
        history=history_payload,
        audit_logs=audit_logs_payload,
        policy_snapshots=policy_snapshots_payload,
    )
    
    # Store result location (in production, this would be a URL to the stored export file)
    import json
    from datetime import datetime
    export_filename = f"export_{request.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    request.result_location = f"https://storage.service/exports/{export_filename}"
    
    # Note: In production, you would write export_data to actual storage here
    # For now, we just set the location

    return export_data


def process_access_request(db: Session, request: SubjectRequest) -> DataAccessResponse:
    """
    Process ACCESS request (Right of Access under GDPR).
    Returns simplified data: user profile + purposes + region (no full history).
    This is different from EXPORT which includes full consent history.
    """
    if request.request_type != RequestTypeEnum.ACCESS:
        raise ValueError("unsupported_request_type")

    user = user_service.get_user(db, request.user_id)
    region, preferences = preferences_service.get_latest_preferences(db, request.user_id)
    purposes_payload: Dict[str, str] = {
        purpose.value: status.value for purpose, status in preferences.items()
    }

    if request.status != RequestStatusEnum.COMPLETED:
        request.status = RequestStatusEnum.COMPLETED
        request.completed_at = get_utc_now()
        db.add(request)
        
        # Log access request completion
        audit = AuditLog(
            user_id=request.user_id,
            action="subject.request.access.completed",
            details={
                "user_id": str(request.user_id),
                "request_id": str(request.id),
            },
            created_at=get_utc_now(),
        )
        db.add(audit)
        db.commit()

    return DataAccessResponse(
        user_id=request.user_id,
        email=user.email,
        region=region,
        purposes=purposes_payload,
    )


def process_delete_request(db: Session, request: SubjectRequest) -> Dict[str, str]:
    if request.request_type != RequestTypeEnum.DELETE:
        raise ValueError("unsupported_request_type")

    if request.status == RequestStatusEnum.COMPLETED:
        return {"status": "completed"}

    user_id = request.user_id
    user = user_service.get_user(db, user_id)
    now = get_utc_now()
    
    import hashlib
    # Generate pseudonymized identifiers
    pseudonym_suffix = hashlib.sha256(f"{user_id}:{now.isoformat()}".encode("utf-8")).hexdigest()[:12]
    
    # Create audit log BEFORE pseudonymization
    audit = AuditLog(
        tenant_id=user.tenant_id,
        subject_id=user_id,
        user_id=user_id,  # Keep user_id for audit trail
        actor_type="system",
        event_type=EventTypeEnum.DELETION_STARTED.value,
        action="subject.request.deletion.started",
        details={
            "user_id": str(user_id),
            "request_id": str(request.id),
            "pseudonym_suffix": pseudonym_suffix,
        },
        event_time=now,
        created_at=now,
    )
    db.add(audit)
    db.flush()
    
    # Pseudonymize user identifiers (replace PII with hashed values)
    user.email = f"deleted-{pseudonym_suffix}@pseudonymized.local"
    user.external_id = f"deleted-{pseudonym_suffix}" if user.external_id else None
    user.primary_identifier_value = f"deleted-{pseudonym_suffix}" if user.primary_identifier_value else None
    user.deleted_at = now
    db.add(user)
    db.flush()
    
    # Optionally purge consents according to retention rules
    # Some regulations require keeping minimal record, so we mark as deleted rather than hard-delete
    # For GDPR, we can delete consents but keep minimal audit trail
    (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_id)
        .delete(synchronize_session=False)
    )
    
    # Delete vendor consents
    from app.models.consent import VendorConsent
    (
        db.query(VendorConsent)
        .filter(VendorConsent.user_id == user_id)
        .delete(synchronize_session=False)
    )
    
    # Delete subject requests except the current one (keep deletion request for audit)
    (
        db.query(SubjectRequest)
        .filter(
            SubjectRequest.user_id == user_id,
            SubjectRequest.id != request.id
        )
        .delete(synchronize_session=False)
    )
    
    # Keep audit logs but remove PII from details where possible
    # Note: We keep user_id in audit logs for legal compliance (minimal audit trail)
    # but the user record is pseudonymized so PII is not directly accessible
    
    # Create completion audit log
    completion_audit = AuditLog(
        tenant_id=user.tenant_id,
        subject_id=user_id,
        user_id=user_id,
        actor_type="system",
        event_type=EventTypeEnum.DELETION_COMPLETED.value,
        action="subject.request.deletion.completed",
        details={
            "user_id": str(user_id),
            "request_id": str(request.id),
            "pseudonymized": True,
        },
        event_time=now,
        created_at=now,
    )
    db.add(completion_audit)
    
    request.status = RequestStatusEnum.COMPLETED
    request.completed_at = now
    
    # Commit all changes together
    db.commit()
    return {"status": "completed"}


def process_rectify_request(
    db: Session,
    user_id: UUID,
    *,
    new_email: str | None,
    new_region: RegionEnum | str | None,
) -> SubjectRequest:
    if not new_email and not new_region:
        raise ValueError("rectify_missing_fields")

    user = user_service.get_user(db, user_id)
    now = get_utc_now()
    changes: Dict[str, str] = {}

    if new_email:
        user.email = user_service.validate_email(new_email)
        changes["email"] = "updated"  # Don't leak PII in audit logs
    if new_region:
        user.region = validate_region(new_region)
        changes["region"] = user.region.value

    request = SubjectRequest(
        user_id=user.id,
        request_type=RequestTypeEnum.RECTIFY,
        status=RequestStatusEnum.COMPLETED,
        requested_at=now,
        completed_at=now,
    )

    audit = AuditLog(
        user_id=user.id,
        action="subject.rectify.completed",
        details={
            "user_id": str(user.id),
            "request_id": str(request.id),
            "changes": changes,
        },
        created_at=now,
    )

    db.add_all([user, request, audit])
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("duplicate_email") from exc

    db.refresh(request)
    return request

