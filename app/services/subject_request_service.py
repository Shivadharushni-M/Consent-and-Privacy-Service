from typing import Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import (
    ConsentHistory,
    RequestStatusEnum,
    RequestTypeEnum,
    SubjectRequest,
)
from app.schemas.consent import ConsentResponse
from app.schemas.subject_requests import DataExportResponse
from app.services import consent_service, preferences_service, user_service
from app.utils.helpers import get_utc_now

SUPPORTED_TYPES = {RequestTypeEnum.EXPORT, RequestTypeEnum.DELETE}


def create_request(db: Session, user_id: UUID, request_type: RequestTypeEnum) -> SubjectRequest:
    if request_type not in SUPPORTED_TYPES:
        raise ValueError("unsupported_request_type")

    user = user_service.get_user(db, user_id)
    request = SubjectRequest(
        user_id=user.id,
        request_type=request_type,
        status=RequestStatusEnum.PENDING,
        requested_at=get_utc_now(),
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

    if request.status != RequestStatusEnum.COMPLETED:
        request.status = RequestStatusEnum.COMPLETED
        request.completed_at = get_utc_now()
        db.add(request)
        db.commit()

    return DataExportResponse(
        user_id=request.user_id,
        region=region,
        preferences=preferences_payload,
        history=history_payload,
    )


def process_delete_request(db: Session, request: SubjectRequest) -> Dict[str, str]:
    if request.request_type != RequestTypeEnum.DELETE:
        raise ValueError("unsupported_request_type")

    if request.status == RequestStatusEnum.COMPLETED:
        return {"status": "completed"}

    (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == request.user_id)
        .delete(synchronize_session=False)
    )
    (
        db.query(SubjectRequest)
        .filter(SubjectRequest.user_id == request.user_id, SubjectRequest.id != request.id)
        .delete(synchronize_session=False)
    )

    request.status = RequestStatusEnum.COMPLETED
    request.completed_at = get_utc_now()

    audit = AuditLog(
        user_id=request.user_id,
        action="subject.request.deleted",
        details={"user_id": str(request.user_id), "request_id": str(request.id)},
        created_at=get_utc_now(),
    )

    db.add_all([request, audit])
    db.commit()
    return {"status": "completed"}


