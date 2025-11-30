from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.consent_v1 import (
    ConsentCreate,
    ConsentQuery,
    ConsentRecordResponse,
    ConsentRevoke,
)
from app.services import consent_v1_service
from app.utils.helpers import extract_client_ip
from app.utils.idempotency import cache_response, get_cached_response
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/consents",
    tags=["consents"],
    dependencies=[Depends(api_key_auth)],
)


@router.post("", response_model=ConsentRecordResponse, status_code=status.HTTP_201_CREATED)
def create_consent(
    consent: ConsentCreate,
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    # Check idempotency
    if x_idempotency_key:
        cached = get_cached_response(db, x_idempotency_key)
        if cached:
            return cached
    
    try:
        # Extract IP and user agent
        ip_address = extract_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        
        record = consent_v1_service.create_consent_record(
            db=db,
            subject_external_id=consent.subject_external_id,
            subject_id=consent.subject_id,
            purpose_code=consent.purpose_code,
            vendor_code=consent.vendor_code,
            legal_basis=consent.legal_basis,
            status=consent.status,
            region_code=consent.region_code,
            valid_from=consent.valid_from,
            valid_until=consent.valid_until,
            policy_version_id=consent.policy_version_id,
            source=consent.source or "api",
            user_agent=user_agent,
            ip_address=ip_address,
            meta=consent.meta,
            tenant_id=consent.tenant_id,
        )
        
        response_data = ConsentRecordResponse.model_validate(record).model_dump()
        
        # Cache response if idempotency key provided
        if x_idempotency_key:
            cache_response(db, x_idempotency_key, response_data)
        
        return response_data
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=List[ConsentRecordResponse])
def list_consents(
    subject_id: Optional[str] = Query(None),
    subject_external_id: Optional[str] = Query(None),
    purpose_code: Optional[str] = Query(None),
    vendor_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        from uuid import UUID
        subject_uuid = UUID(subject_id) if subject_id else None
        records = consent_v1_service.query_consents(
            db=db,
            subject_id=subject_uuid,
            subject_external_id=subject_external_id,
            purpose_code=purpose_code,
            vendor_code=vendor_code,
            status=status,
            tenant_id=tenant_id,
        )
        return records
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/revoke", response_model=ConsentRecordResponse, status_code=status.HTTP_201_CREATED)
def revoke_consent(
    payload: ConsentRevoke,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    # Check idempotency
    if x_idempotency_key:
        cached = get_cached_response(db, x_idempotency_key)
        if cached:
            return cached
    
    try:
        record = consent_v1_service.revoke_consent_record(
            db=db,
            subject_external_id=payload.subject_external_id,
            subject_id=payload.subject_id,
            purpose_code=payload.purpose_code,
            vendor_code=payload.vendor_code,
            reason=payload.reason,
            tenant_id=payload.tenant_id,
        )
        
        response_data = ConsentRecordResponse.model_validate(record).model_dump()
        
        # Cache response if idempotency key provided
        if x_idempotency_key:
            cache_response(db, x_idempotency_key, response_data)
        
        return response_data
    except ValueError as exc:
        if str(exc) == "no_active_consent":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
