import hashlib
from typing import Dict
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.audit import AuditLog, EventTypeEnum
from app.models.consent import ConsentHistory, RegionEnum, RequestStatusEnum, RequestTypeEnum, SubjectRequest
from app.schemas.consent import ConsentResponse
from app.schemas.subject_requests import DataAccessResponse, DataExportResponse
from app.services import consent_service, preferences_service, user_service
from app.utils.helpers import get_utc_now, validate_region

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
    preferences_payload: Dict[str, str] = {purpose.value: status.value for purpose, status in preferences.items()}
    history_payload = [ConsentResponse.model_validate(record) for record in history_records]
    audit_logs = db.query(AuditLog).filter((AuditLog.subject_id == request.user_id) | (AuditLog.user_id == request.user_id)).order_by(AuditLog.event_time.desc()).all()
    audit_logs_payload = [{"id": str(log.id), "event_type": log.event_type, "action": log.action, "event_time": log.event_time.isoformat() if log.event_time else None, "details": log.details, "policy_snapshot": log.policy_snapshot} for log in audit_logs]
    seen_snapshots: set = set()
    policy_snapshots_payload = []
    for item in history_records + audit_logs:
        if item.policy_snapshot:
            key = str(sorted(item.policy_snapshot.items())) if isinstance(item.policy_snapshot, dict) else str(item.policy_snapshot)
            if key not in seen_snapshots:
                seen_snapshots.add(key)
                policy_snapshots_payload.append(item.policy_snapshot)
    request.result_location = f"https://storage.service/exports/export_{request.user_id}_{get_utc_now().strftime('%Y%m%d_%H%M%S')}.json"
    return DataExportResponse(user_id=request.user_id, region=region, preferences=preferences_payload, history=history_payload, audit_logs=audit_logs_payload, policy_snapshots=policy_snapshots_payload)


def process_access_request(db: Session, request: SubjectRequest) -> DataAccessResponse:
    if request.request_type != RequestTypeEnum.ACCESS:
        raise ValueError("unsupported_request_type")
    user = user_service.get_user(db, request.user_id)
    region, preferences = preferences_service.get_latest_preferences(db, request.user_id)
    purposes_payload: Dict[str, str] = {purpose.value: status.value for purpose, status in preferences.items()}
    if request.status != RequestStatusEnum.COMPLETED:
        request.status = RequestStatusEnum.COMPLETED
        request.completed_at = get_utc_now()
        db.add(request)
        db.add(AuditLog(user_id=request.user_id, action="subject.request.access.completed", details={"user_id": str(request.user_id), "request_id": str(request.id)}, created_at=get_utc_now()))
        db.commit()
    return DataAccessResponse(user_id=request.user_id, email=user.email, region=region, purposes=purposes_payload)


def process_delete_request(db: Session, request: SubjectRequest) -> Dict[str, str]:
    if request.request_type != RequestTypeEnum.DELETE:
        raise ValueError("unsupported_request_type")
    if request.status == RequestStatusEnum.COMPLETED:
        return {"status": "completed"}
    user = user_service.get_user(db, request.user_id)
    now = get_utc_now()
    pseudonym_suffix = hashlib.sha256(f"{request.user_id}:{now.isoformat()}".encode("utf-8")).hexdigest()[:12]
    db.add(AuditLog(tenant_id=user.tenant_id, subject_id=request.user_id, user_id=request.user_id, actor_type="system", event_type=EventTypeEnum.DELETION_STARTED.value, action="subject.request.deletion.started", details={"user_id": str(request.user_id), "request_id": str(request.id), "pseudonym_suffix": pseudonym_suffix}, event_time=now, created_at=now))
    user.email = f"deleted-{pseudonym_suffix}@pseudonymized.local"
    user.external_id = f"deleted-{pseudonym_suffix}" if user.external_id else None
    user.primary_identifier_value = f"deleted-{pseudonym_suffix}" if user.primary_identifier_value else None
    user.deleted_at = now
    db.query(ConsentHistory).filter(ConsentHistory.user_id == request.user_id).delete(synchronize_session=False)
    db.query(SubjectRequest).filter(SubjectRequest.user_id == request.user_id, SubjectRequest.id != request.id).delete(synchronize_session=False)
    db.add(AuditLog(tenant_id=user.tenant_id, subject_id=request.user_id, user_id=request.user_id, actor_type="system", event_type=EventTypeEnum.DELETION_COMPLETED.value, action="subject.request.deletion.completed", details={"user_id": str(request.user_id), "request_id": str(request.id), "pseudonymized": True}, event_time=now, created_at=now))
    request.status = RequestStatusEnum.COMPLETED
    request.completed_at = now
    db.commit()
    return {"status": "completed"}


def process_rectify_request(db: Session, user_id: UUID, *, new_email: str | None, new_region: RegionEnum | str | None) -> SubjectRequest:
    if not new_email and not new_region:
        raise ValueError("rectify_missing_fields")
    user = user_service.get_user(db, user_id)
    now = get_utc_now()
    changes: Dict[str, str] = {}
    if new_email:
        user.email = user_service.validate_email(new_email)
        changes["email"] = "updated"
    if new_region:
        user.region = validate_region(new_region)
        changes["region"] = user.region.value
    request = SubjectRequest(user_id=user.id, request_type=RequestTypeEnum.RECTIFY, status=RequestStatusEnum.COMPLETED, requested_at=now, completed_at=now)
    db.add_all([user, request, AuditLog(user_id=user.id, action="subject.rectify.completed", details={"user_id": str(user.id), "request_id": str(request.id), "changes": changes}, created_at=now)])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("duplicate_email")
    db.refresh(request)
    return request

