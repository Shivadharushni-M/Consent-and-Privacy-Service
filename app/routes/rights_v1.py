import logging
from typing import Any, Dict, Optional
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.db.database import get_db

logger = logging.getLogger(__name__)
from app.models.consent import RequestTypeEnum, RequestStatusEnum
from app.models.tokens import TokenPurposeEnum, VerificationToken
from app.schemas.rights import (
    DeleteRequestCreate,
    ExportRequestCreate,
    RightsRequestResponse,
    VerifyRequest,
)
from app.services import subject_service, subject_request_service
from app.utils.helpers import get_utc_now
from app.utils.idempotency import cache_response, get_cached_response
from app.utils.security import api_key_auth, generate_verification_token, verify_token

router = APIRouter(
    prefix="/api/v1/rights",
    tags=["rights"],
    dependencies=[Depends(api_key_auth)],
)

admin_router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-rights"],
    dependencies=[Depends(api_key_auth)],
)


@router.post("/export-requests", response_model=RightsRequestResponse, status_code=status.HTTP_201_CREATED)
def create_export_request(
    request: ExportRequestCreate,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    if x_idempotency_key:
        cached = get_cached_response(db, x_idempotency_key)
        if cached:
            return cached
    
    try:
        # Resolve subject
        if request.subject_id:
            logger.info(f"[EXPORT] Looking up subject by ID: {request.subject_id}, tenant: {request.tenant_id}")
            from app.services.user_service import get_user
            user = get_user(db, request.subject_id)
        elif request.subject_external_id:
            logger.info(f"[EXPORT] Looking up subject by external_id: {request.subject_external_id}, tenant: {request.tenant_id}")
            user = subject_service.get_subject_by_external_id(db, request.subject_external_id, request.tenant_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="subject_id or subject_external_id required"
            )
        
        logger.info(f"[EXPORT] Found subject: {user.id}, creating export request")
        # Create verification token
        token_data = {
            "user_id": str(user.id),
            "request_type": RequestTypeEnum.EXPORT.value,
        }
        token = generate_verification_token(token_data)
        
        # Create token record
        token_record = VerificationToken(
            token=token,
            purpose=TokenPurposeEnum.RIGHTS_EXPORT.value,
            subject_id=user.id,
            tenant_id=request.tenant_id,
            expires_at=get_utc_now() + timedelta(days=7),
            meta=request.notification_channel or {},
        )
        db.add(token_record)
        db.flush()
        
        # Create request
        rights_request = subject_request_service.create_request(
            db, user.id, RequestTypeEnum.EXPORT
        )
        rights_request.verification_token_id = token_record.id
        rights_request.tenant_id = request.tenant_id
        rights_request.requested_by = "subject"
        db.commit()
        db.refresh(rights_request)
        
        response_data = RightsRequestResponse.model_validate(rights_request).model_dump()
        # Include the actual token in the response
        response_data["verification_token"] = token
        if x_idempotency_key:
            cache_response(db, x_idempotency_key, response_data)
        
        return response_data
    except ValueError as exc:
        error_msg = str(exc)
        logger.error(f"[EXPORT] Error: {error_msg} for subject_id={request.subject_id}, subject_external_id={request.subject_external_id}, tenant_id={request.tenant_id}")
        # Map specific errors to appropriate status codes
        if error_msg == "subject_not_found" or error_msg == "user_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{error_msg}. Please create the subject first using POST /api/v1/subjects"
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            ) from exc


@router.post("/delete-requests", response_model=RightsRequestResponse, status_code=status.HTTP_201_CREATED)
def create_delete_request(
    request: DeleteRequestCreate,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    if x_idempotency_key:
        cached = get_cached_response(db, x_idempotency_key)
        if cached:
            return cached
    
    try:
        # Resolve subject
        if request.subject_id:
            logger.info(f"[DELETE] Looking up subject by ID: {request.subject_id}, tenant: {request.tenant_id}")
            from app.services.user_service import get_user
            user = get_user(db, request.subject_id)
        elif request.subject_external_id:
            logger.info(f"[DELETE] Looking up subject by external_id: {request.subject_external_id}, tenant: {request.tenant_id}")
            user = subject_service.get_subject_by_external_id(db, request.subject_external_id, request.tenant_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="subject_id or subject_external_id required"
            )
        
        logger.info(f"[DELETE] Found subject: {user.id}, creating delete request")
        # Create verification token
        token_data = {
            "user_id": str(user.id),
            "request_type": RequestTypeEnum.DELETE.value,
        }
        token = generate_verification_token(token_data)
        
        # Create token record
        token_record = VerificationToken(
            token=token,
            purpose=TokenPurposeEnum.RIGHTS_DELETION.value,
            subject_id=user.id,
            tenant_id=request.tenant_id,
            expires_at=get_utc_now() + timedelta(days=7),
            meta=request.notification_channel or {},
        )
        db.add(token_record)
        db.flush()
        
        # Create request
        rights_request = subject_request_service.create_request(
            db, user.id, RequestTypeEnum.DELETE
        )
        rights_request.verification_token_id = token_record.id
        rights_request.tenant_id = request.tenant_id
        rights_request.requested_by = "subject"
        db.commit()
        db.refresh(rights_request)
        
        response_data = RightsRequestResponse.model_validate(rights_request).model_dump()
        # Include the actual token in the response
        response_data["verification_token"] = token
        if x_idempotency_key:
            cache_response(db, x_idempotency_key, response_data)
        
        return response_data
    except ValueError as exc:
        error_msg = str(exc)
        logger.error(f"[DELETE] Error: {error_msg} for subject_id={request.subject_id}, subject_external_id={request.subject_external_id}, tenant_id={request.tenant_id}")
        # Map specific errors to appropriate status codes
        if error_msg == "subject_not_found" or error_msg == "user_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{error_msg}. Please create the subject first using POST /api/v1/subjects"
            ) from exc
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            ) from exc


@router.post("/verify", response_model=RightsRequestResponse)
def verify_rights_request(
    payload: VerifyRequest,
    db: Session = Depends(get_db),
):
    verified_data = verify_token(payload.token)
    if not verified_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    
    # Find token record
    token_record = db.query(VerificationToken).filter(
        VerificationToken.token == payload.token,
        VerificationToken.used_at.is_(None),
        VerificationToken.expires_at > get_utc_now(),
    ).first()
    
    if not token_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_not_found_or_expired")
    
    # Mark as used
    token_record.used_at = get_utc_now()
    
    # Find request
    from app.models.consent import SubjectRequest, RequestTypeEnum, RequestStatusEnum
    from app.models.audit import AuditLog, EventTypeEnum
    request_type = RequestTypeEnum(verified_data.get("request_type"))
    request = db.query(SubjectRequest).filter(
        SubjectRequest.user_id == token_record.subject_id,
        SubjectRequest.request_type == request_type,
        SubjectRequest.status == RequestStatusEnum.PENDING_VERIFICATION,
    ).first()
    
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")
    
    # Mark as verified and trigger processing
    request.verification_token_id = token_record.id
    request.status = RequestStatusEnum.VERIFIED
    
    # Log verification
    audit = AuditLog(
        tenant_id=request.tenant_id,
        subject_id=token_record.subject_id,
        actor_type="subject",
        event_type=EventTypeEnum.EXPORT_REQUESTED.value if request_type == RequestTypeEnum.EXPORT else EventTypeEnum.DELETION_STARTED.value,
        action="rights_request_verified",
        details={
            "request_id": str(request.id),
            "request_type": request_type.value,
        },
        event_time=get_utc_now(),
    )
    db.add(audit)
    db.flush()
    
    # Trigger background processing
    try:
        if request_type == RequestTypeEnum.EXPORT:
            request.status = RequestStatusEnum.PROCESSING
            db.flush()
            # Process export synchronously (can be moved to background job if needed)
            from app.services.subject_request_service import process_export_request
            export_result = process_export_request(db, request)
            # result_location is set in process_export_request
            # Ensure request is in session and commit
            db.add(request)
            request.status = RequestStatusEnum.COMPLETED
            request.completed_at = get_utc_now()
            db.commit()
        elif request_type == RequestTypeEnum.DELETE:
            request.status = RequestStatusEnum.PROCESSING
            db.flush()
            # Process deletion synchronously (can be moved to background job if needed)
            # Note: process_delete_request commits internally, so we don't commit again
            from app.services.subject_request_service import process_delete_request
            process_delete_request(db, request)
            # Status is already set to COMPLETED in process_delete_request
            # Re-query the request since it was committed in a different transaction
            from app.models.consent import SubjectRequest
            request = db.get(SubjectRequest, request.id)
        else:
            raise ValueError(f"Unsupported request type: {request_type}")
    except Exception as e:
        # Only rollback if we haven't committed yet
        if request.status != RequestStatusEnum.COMPLETED:
            request.status = RequestStatusEnum.FAILED
            request.error_message = str(e)
            db.add(request)
            db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Processing failed: {str(e)}")
    
    db.refresh(request)
    return RightsRequestResponse.model_validate(request)


@router.get("/requests/{request_id}", response_model=RightsRequestResponse)
def get_rights_request(request_id: UUID, db: Session = Depends(get_db)):
    from app.models.consent import SubjectRequest
    request = db.get(SubjectRequest, request_id)
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return request


@router.get("/admin/exports/{request_id}", response_model=Dict[str, Any])
def get_export_details(request_id: UUID, db: Session = Depends(get_db)):
    from app.models.consent import SubjectRequest, RequestTypeEnum
    request = db.get(SubjectRequest, request_id)
    if not request or request.request_type != RequestTypeEnum.EXPORT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export request not found")
    
    return {
        "id": str(request.id),
        "status": request.status.value,
        "result_location": request.result_location,
        "error_message": request.error_message,
    }


@admin_router.get("/deletions/{request_id}", response_model=Dict[str, Any])
def get_deletion_details(request_id: UUID, db: Session = Depends(get_db)):
    from app.models.consent import SubjectRequest, RequestTypeEnum
    request = db.get(SubjectRequest, request_id)
    if not request or request.request_type != RequestTypeEnum.DELETE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deletion request not found")
    
    return {
        "id": str(request.id),
        "status": request.status.value,
        "error_message": request.error_message,
    }
