from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.consent import CreateConsentRequest, ConsentResponse
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])

@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    consent = consent_service.grant_consent(
        db=db,
        user_id=request.user_id,
        purpose=request.purpose,
        region=request.region,
        policy_snapshot=request.policy_snapshot
    )
    return consent

@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    consent = consent_service.revoke_consent(
        db=db,
        user_id=request.user_id,
        purpose=request.purpose,
        region=request.region,
        policy_snapshot=request.policy_snapshot
    )
    return consent

@router.get("/history/{user_id}", response_model=List[ConsentResponse])
def get_consent_history(user_id: int, db: Session = Depends(get_db)):
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    history = consent_service.get_history(db=db, user_id=user_id)
    return history

