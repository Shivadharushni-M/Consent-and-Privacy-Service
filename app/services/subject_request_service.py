import hashlib
from typing import Dict, Optional, Union
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.audit import AuditLog, EventTypeEnum
from app.models.consent import ConsentHistory, RegionEnum, RequestStatusEnum, RequestTypeEnum, SubjectRequest, User
from app.schemas.consent import ConsentResponse
from app.schemas.subject_requests import DataAccessResponse, DataExportResponse
from app.services import consent_service, preferences_service, user_service
from app.utils.helpers import get_audit_log_kwargs, get_utc_now, validate_region
from app.utils.security import Actor

SUPPORTED_TYPES = {RequestTypeEnum.EXPORT, RequestTypeEnum.DELETE, RequestTypeEnum.ACCESS}


def create_request(db: Session, user_id: UUID, request_type: RequestTypeEnum, actor: Optional[Union[Actor, User]] = None) -> SubjectRequest:
    if request_type not in SUPPORTED_TYPES:
        raise ValueError("unsupported_request_type")
    user = user_service.get_user(db, user_id)
    now = get_utc_now()
    request = SubjectRequest(user_id=user.id, request_type=request_type, status=RequestStatusEnum.PENDING_VERIFICATION, requested_at=now)
    db.add_all([request, AuditLog(action="subject.request.created", details={"user_id": str(user.id), "request_id": str(request.id), "request_type": request_type.value}, created_at=now, **get_audit_log_kwargs(actor, user_id=user.id))])
    db.commit()
    db.refresh(request)
    return request


def _mark_request_completed(db: Session, request: SubjectRequest, action: str, actor: Optional[Union[Actor, User]] = None) -> None:
    if request.status != RequestStatusEnum.COMPLETED:
        request.status = RequestStatusEnum.COMPLETED
        request.completed_at = get_utc_now()
        db.add(request)
        db.add(AuditLog(action=action, details={"user_id": str(request.user_id), "request_id": str(request.id)}, created_at=get_utc_now(), **get_audit_log_kwargs(actor, user_id=request.user_id)))
        db.commit()


def process_export_request(db: Session, request: SubjectRequest, actor: Optional[Union[Actor, User]] = None) -> DataExportResponse:
    if request.request_type != RequestTypeEnum.EXPORT:
        raise ValueError("unsupported_request_type")
    region, preferences = preferences_service.get_latest_preferences(db, request.user_id)
    history_records = consent_service.get_history(db, request.user_id)
    audit_logs = db.query(AuditLog).filter((AuditLog.subject_id == request.user_id) | (AuditLog.user_id == request.user_id)).order_by(AuditLog.event_time.desc()).all()
    seen_snapshots, policy_snapshots_payload = set(), []
    for item in history_records + audit_logs:
        if item.policy_snapshot:
            key = str(sorted(item.policy_snapshot.items())) if isinstance(item.policy_snapshot, dict) else str(item.policy_snapshot)
            if key not in seen_snapshots:
                seen_snapshots.add(key)
                policy_snapshots_payload.append(item.policy_snapshot)
    request.result_location = f"https://storage.service/exports/export_{request.user_id}_{get_utc_now().strftime('%Y%m%d_%H%M%S')}.json"
    _mark_request_completed(db, request, "subject.request.export.completed", actor)
    return DataExportResponse(user_id=request.user_id, region=region, preferences={p.value: s.value for p, s in preferences.items()}, history=[ConsentResponse.model_validate(r) for r in history_records], audit_logs=[{"id": str(log.id), "event_type": log.event_type, "action": log.action, "event_time": log.event_time.isoformat() if log.event_time else None, "details": log.details, "policy_snapshot": log.policy_snapshot} for log in audit_logs], policy_snapshots=policy_snapshots_payload)


def process_access_request(db: Session, request: SubjectRequest, actor: Optional[Union[Actor, User]] = None) -> DataAccessResponse:
    if request.request_type != RequestTypeEnum.ACCESS:
        raise ValueError("unsupported_request_type")
    user = user_service.get_user(db, request.user_id)
    region, preferences = preferences_service.get_latest_preferences(db, request.user_id)
    _mark_request_completed(db, request, "subject.request.access.completed", actor)
    return DataAccessResponse(user_id=request.user_id, email=user.email, region=region, purposes={p.value: s.value for p, s in preferences.items()})


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
    if user.external_id:
        user.external_id = f"deleted-{pseudonym_suffix}"
    if user.primary_identifier_value:
        user.primary_identifier_value = f"deleted-{pseudonym_suffix}"
    user.deleted_at = now
    db.query(ConsentHistory).filter(ConsentHistory.user_id == request.user_id).delete(synchronize_session=False)
    db.query(SubjectRequest).filter(SubjectRequest.user_id == request.user_id, SubjectRequest.id != request.id).delete(synchronize_session=False)
    db.add(AuditLog(tenant_id=user.tenant_id, subject_id=request.user_id, user_id=request.user_id, actor_type="system", event_type=EventTypeEnum.DELETION_COMPLETED.value, action="subject.request.deletion.completed", details={"user_id": str(request.user_id), "request_id": str(request.id), "pseudonymized": True}, event_time=now, created_at=now))
    request.status, request.completed_at = RequestStatusEnum.COMPLETED, now
    db.commit()
    return {"status": "completed"}


def process_rectify_request(db: Session, user_id: UUID, *, new_region: RegionEnum | str | None, actor: Optional[Union[Actor, User]] = None) -> SubjectRequest:
    if not new_region:
        raise ValueError("rectify_missing_fields")
    user = user_service.get_user(db, user_id)
    now = get_utc_now()
    user.region = validate_region(new_region)
    request = SubjectRequest(user_id=user.id, request_type=RequestTypeEnum.RECTIFY, status=RequestStatusEnum.COMPLETED, requested_at=now, completed_at=now)
    db.add_all([user, request, AuditLog(action="subject.rectify.completed", details={"user_id": str(user.id), "request_id": str(request.id), "changes": {"region": user.region.value}}, created_at=now, **get_audit_log_kwargs(actor, user_id=user.id))])
    db.commit()
    db.refresh(request)
    return request

