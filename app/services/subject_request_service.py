from typing import Dict
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
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
    token = generate_verification_token({"user_id": str(user.id), "request_type": request_type.value})
    request = SubjectRequest(
        user_id=user.id,
        request_type=request_type,
        status=RequestStatusEnum.PENDING,
        requested_at=get_utc_now(),
        verification_token=token,
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

    # Create audit log and set user_id to None to prevent CASCADE deletion
    audit = AuditLog(
        user_id=user_id,
        action="subject.request.deleted",
        details={"user_id": str(user_id), "request_id": str(request.id)},
        created_at=get_utc_now(),
    )
    db.add(audit)
    db.flush()  # Write audit log first

    # Set user_id to None on all audit logs for this user to prevent CASCADE deletion
    db.query(AuditLog).filter(AuditLog.user_id == user_id).update(
        {"user_id": None}, synchronize_session=False
    )

    # Delete all user data except audit logs
    (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_id)
        .delete(synchronize_session=False)
    )
    (
        db.query(SubjectRequest)
        .filter(SubjectRequest.user_id == user_id)
        .delete(synchronize_session=False)
    )

    # Delete vendor consents if they exist
    from app.models.consent import VendorConsent

    (
        db.query(VendorConsent)
        .filter(VendorConsent.user_id == user_id)
        .delete(synchronize_session=False)
    )

    # Delete the user record itself
    from app.models.consent import User

    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)

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

