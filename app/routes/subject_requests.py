from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import RequestTypeEnum, SubjectRequest
from app.schemas.subject_requests import (
    DataAccessResponse,
    DataExportResponse,
    SubjectRequestIn,
    SubjectRequestOut,
)
from app.services import subject_request_service
from app.utils.security import api_key_auth, verify_token

router = APIRouter(
    prefix="/subject-requests",
    tags=["subject-requests"],
    dependencies=[Depends(api_key_auth)],
)

_ERROR_MAP = {
    "user_not_found": (status.HTTP_404_NOT_FOUND, "user_not_found"),
    "unsupported_request_type": (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "unsupported_request_type",
    ),
    "rectify_missing_fields": (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "missing_rectification_fields",
    ),
    "duplicate_email": (status.HTTP_409_CONFLICT, "email_conflict"),
}


def _handle_error(exc: ValueError) -> None:
    status_code, detail = _ERROR_MAP.get(
        str(exc), (status.HTTP_400_BAD_REQUEST, "invalid_request")
    )
    raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("", response_model=SubjectRequestOut, status_code=status.HTTP_201_CREATED)
def create_subject_request(payload: SubjectRequestIn, db: Session = Depends(get_db)):
    try:
        if payload.request_type == RequestTypeEnum.RECTIFY:
            request = subject_request_service.process_rectify_request(
                db,
                payload.user_id,
                new_email=payload.new_email,
                new_region=payload.new_region,
            )
        else:
            request = subject_request_service.create_request(
                db, payload.user_id, payload.request_type
            )
        return SubjectRequestOut(
            request_id=request.id,
            status=request.status,
            request_type=request.request_type,
            verification_token=request.verification_token,
        )
    except ValueError as exc:
        _handle_error(exc)


@router.get("/export/{request_id}", response_model=DataExportResponse)
def process_export_request(
    request_id: UUID,
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db),
):
    """Process EXPORT request - returns full data export including consent history."""
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")

    if request.request_type != RequestTypeEnum.EXPORT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request type must be EXPORT for this endpoint",
        )

    # Verify token
    if request.verification_token and request.verification_token == token:
        pass  # Token matches stored value
    else:
        verified_data = verify_token(token)
        if not verified_data or str(request.user_id) != verified_data.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
            )

    return subject_request_service.process_export_request(db, request)


@router.get("/access/{request_id}", response_model=DataAccessResponse)
def process_access_request(
    request_id: UUID,
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db),
):
    """Process ACCESS request (GDPR Right of Access) - returns simplified view of user data."""
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")

    if request.request_type != RequestTypeEnum.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request type must be ACCESS for this endpoint",
        )

    # Verify token
    if request.verification_token and request.verification_token == token:
        pass  # Token matches stored value
    else:
        verified_data = verify_token(token)
        if not verified_data or str(request.user_id) != verified_data.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
            )

    return subject_request_service.process_access_request(db, request)


@router.get("/{request_id}")
def process_subject_request(
    request_id: UUID,
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db),
):
    """Legacy endpoint - routes to appropriate handler based on request type."""
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")

    # Verify token - check stored token first, then verify via itsdangerous
    if request.verification_token and request.verification_token == token:
        pass  # Token matches stored value
    else:
        verified_data = verify_token(token)
        if not verified_data or str(request.user_id) != verified_data.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
            )

    if request.request_type == RequestTypeEnum.EXPORT:
        return subject_request_service.process_export_request(db, request)
    if request.request_type == RequestTypeEnum.ACCESS:
        return subject_request_service.process_access_request(db, request)
    if request.request_type == RequestTypeEnum.DELETE:
        return subject_request_service.process_delete_request(db, request)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported_request_type"
    )


