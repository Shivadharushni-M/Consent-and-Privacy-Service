from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import RequestTypeEnum, SubjectRequest
from app.models.tokens import TokenPurposeEnum, VerificationToken
from app.schemas.subject_requests import (
    DataAccessResponse,
    DataExportResponse,
    SubjectRequestIn,
    SubjectRequestOut,
)
from app.services import subject_request_service
from app.utils.helpers import get_utc_now
from app.utils.security import api_key_auth, generate_verification_token, verify_token

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
            # RECTIFY requests don't need verification tokens
            return SubjectRequestOut(
                request_id=request.id,
                status=request.status,
                request_type=request.request_type,
                verification_token=None,
            )
        else:
            request = subject_request_service.create_request(
                db, payload.user_id, payload.request_type
            )
            
            # Generate verification token
            token_data = {
                "user_id": str(request.user_id),
                "request_type": payload.request_type.value,
            }
            token = generate_verification_token(token_data)
            
            # Determine token purpose based on request type
            if payload.request_type == RequestTypeEnum.EXPORT:
                purpose = TokenPurposeEnum.RIGHTS_EXPORT
            elif payload.request_type == RequestTypeEnum.DELETE:
                purpose = TokenPurposeEnum.RIGHTS_DELETION
            elif payload.request_type == RequestTypeEnum.ACCESS:
                purpose = TokenPurposeEnum.RIGHTS_ACCESS
            else:
                # For other types, use RIGHTS_EXPORT as default
                purpose = TokenPurposeEnum.RIGHTS_EXPORT
            
            # Create token record
            token_record = VerificationToken(
                token=token,
                purpose=purpose.value,
                subject_id=request.user_id,
                tenant_id=request.tenant_id,
                expires_at=get_utc_now() + timedelta(days=7),
            )
            db.add(token_record)
            db.flush()
            
            # Link token to request
            request.verification_token_id = token_record.id
            db.commit()
            db.refresh(request)
            
            return SubjectRequestOut(
                request_id=request.id,
                status=request.status,
                request_type=request.request_type,
                verification_token=token,
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
    verified_data = verify_token(token)
    if not verified_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token matches request
    if str(request.user_id) != verified_data.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token request_type matches endpoint expectation
    token_request_type = verified_data.get("request_type")
    if token_request_type != RequestTypeEnum.EXPORT.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Token is for request type '{token_request_type}', but this endpoint requires 'export'",
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
    verified_data = verify_token(token)
    if not verified_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token matches request
    if str(request.user_id) != verified_data.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token request_type matches endpoint expectation
    token_request_type = verified_data.get("request_type")
    if token_request_type != RequestTypeEnum.ACCESS.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Token is for request type '{token_request_type}', but this endpoint requires 'access'",
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

    # Verify token
    verified_data = verify_token(token)
    if not verified_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token matches request
    if str(request.user_id) != verified_data.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_verification_token"
        )
    
    # Verify token request_type matches the request's type
    token_request_type = verified_data.get("request_type")
    if token_request_type != request.request_type.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Token is for request type '{token_request_type}', but request is '{request.request_type.value}'",
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
