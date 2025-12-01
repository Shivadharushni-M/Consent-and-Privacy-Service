from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import VendorEnum
from app.schemas.vendor_consent import (
    CreateVendorConsentRequest,
    VendorConsentResponse,
)
from app.services import vendor_consent_service
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/vendor-consent",
    tags=["vendor-consent"],
    dependencies=[Depends(api_key_auth)],
)


def _handle_service_errors(exc: ValueError) -> None:
    if str(exc) == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found") from exc
    if str(exc) == "invalid_region":
        raise HTTPException(status_code=422, detail="Invalid region") from exc
    raise HTTPException(status_code=400, detail="Invalid request") from exc


@router.post("/grant", response_model=VendorConsentResponse, status_code=201)
def grant_vendor_consent(
    request: CreateVendorConsentRequest, db: Session = Depends(get_db)
):
    try:
        return vendor_consent_service.grant_vendor_consent(
            db=db,
            user_id=request.user_id,
            vendor=request.vendor,
            purpose=request.purpose,
            region=request.region,
            expires_at=request.expires_at,
        )
    except ValueError as exc:
        _handle_service_errors(exc)


@router.post("/revoke", response_model=VendorConsentResponse, status_code=201)
def revoke_vendor_consent(
    request: CreateVendorConsentRequest, db: Session = Depends(get_db)
):
    try:
        return vendor_consent_service.revoke_vendor_consent(
            db=db,
            user_id=request.user_id,
            vendor=request.vendor,
            purpose=request.purpose,
            region=request.region,
            expires_at=request.expires_at,
        )
    except ValueError as exc:
        _handle_service_errors(exc)


@router.get("/history/{user_id}", response_model=List[VendorConsentResponse])
def get_vendor_consent_history(
    user_id: UUID,
    vendor: Optional[VendorEnum] = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        return vendor_consent_service.get_vendor_history(db=db, user_id=user_id, vendor=vendor)
    except ValueError as exc:
        _handle_service_errors(exc)
