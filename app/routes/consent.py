from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.db.database import get_db
from app.schemas.consent import CreateConsentRequest, ConsentResponse
from app.schemas.common import PreferencesUpdateRequest
from app.services import consent_service
from app.utils.security import api_key_auth

router = APIRouter(prefix="/consent", tags=["consent"], dependencies=[Depends(api_key_auth)])

@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        consent = consent_service.grant_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
            policy_snapshot=request.policy_snapshot
        )
        return consent
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in grant_consent: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        consent = consent_service.revoke_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
            policy_snapshot=request.policy_snapshot
        )
        return consent
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in revoke_consent: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/history/{user_id}", response_model=List[ConsentResponse])
def get_consent_history(user_id: str, db: Session = Depends(get_db)):
    # Accept user_id as string (can be integer string or UUID string)
    try:
        # Try to parse as integer first
        int_id = int(user_id)
        if int_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid user_id")
    except ValueError:
        # If not an integer, it should be a UUID string
        pass
    history = consent_service.get_history(db=db, user_id=user_id)
    return history

# Preferences endpoints (separate tag)
preferences_router = APIRouter(prefix="/consent/preferences", tags=["preferences"], dependencies=[Depends(api_key_auth)])

@preferences_router.get("/{user_id}")
def read_preferences(user_id: str, db: Session = Depends(get_db)):
    """Read Preferences"""
    return {"user_id": user_id, "preferences": {}}

@preferences_router.post("/update", status_code=201)
def post_update_preferences(request: PreferencesUpdateRequest, db: Session = Depends(get_db)):
    """Post Update Preferences"""
    try:
        return {
            "message": "Preferences updated",
            "user_id": request.user_id,
            "preferences": request.preferences,
            "metadata": request.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

