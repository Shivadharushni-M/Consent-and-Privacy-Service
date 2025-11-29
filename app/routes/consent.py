from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.consent import ConsentResponse, CreateConsentRequest
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


def _handle_service_errors(exc: ValueError) -> None:
    if str(exc) == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found") from exc
    if str(exc) == "invalid_region":
        raise HTTPException(status_code=422, detail="Invalid region") from exc
    raise HTTPException(status_code=400, detail="Invalid request") from exc


@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        return consent_service.grant_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
        )
    except ValueError as exc:
        _handle_service_errors(exc)


@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        return consent_service.revoke_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
        )
    except ValueError as exc:
        _handle_service_errors(exc)


@router.get("/history/{user_id}", response_model=List[ConsentResponse])
def get_consent_history(user_id: UUID, db: Session = Depends(get_db)):
    try:
        return consent_service.get_history(db=db, user_id=user_id)
    except ValueError as exc:
        _handle_service_errors(exc)
