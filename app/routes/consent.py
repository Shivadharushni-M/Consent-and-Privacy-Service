from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.consent import ConsentResponse, CreateConsentRequest
from app.schemas.preferences import PreferencesResponse, PreferencesUpdateRequest
from app.services import consent_service
from app.services.preferences_service import update_preferences
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/consent",
    tags=["consent"],
    dependencies=[Depends(api_key_auth)],
)


def _handle_service_errors(exc: Exception) -> None:
    """Handle service errors and convert them to HTTPExceptions."""
    # Ensure we always get a string representation
    try:
        error_str = str(exc) if exc else "Unknown error"
    except Exception:
        error_str = f"Error of type {type(exc).__name__}"
    
    # Handle specific error codes
    if error_str == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found") from exc
    if error_str == "invalid_region":
        raise HTTPException(status_code=422, detail="Invalid region") from exc
    if error_str.startswith("database_error"):
        # Extract the actual error message if available
        detail = error_str.replace("database_error: ", "") if "database_error: " in error_str else "Database error occurred"
        raise HTTPException(status_code=500, detail=detail) from exc
    
    # For ValueError exceptions, use the message
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=error_str) from exc
    
    # For any other exception, return a generic error
    raise HTTPException(status_code=500, detail=f"Internal server error: {error_str}") from exc


@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        # Get expires_at from the request
        expires_at = request.get_expires_at()
        
        return consent_service.grant_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
            expires_at=expires_at,
        )
    except ValueError as exc:
        # Handle ValueError specifically
        _handle_service_errors(exc)
    except Exception as exc:
        # Handle any other exceptions
        _handle_service_errors(exc)


@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        return consent_service.revoke_consent(
            db=db,
            user_id=request.user_id,
            purpose=request.purpose,
            region=request.region,
            expires_at=request.get_expires_at() if hasattr(request, 'get_expires_at') else None,
        )
    except Exception as exc:
        _handle_service_errors(exc)


@router.get("/history/{user_id}", response_model=List[ConsentResponse])
def get_consent_history(user_id: UUID, db: Session = Depends(get_db)):
    try:
        return consent_service.get_history(db=db, user_id=user_id)
    except Exception as exc:
        _handle_service_errors(exc)


# Preferences endpoints (separate tag)
preferences_router = APIRouter(prefix="/consent/preferences", tags=["preferences"], dependencies=[Depends(api_key_auth)])

@preferences_router.get("/{user_id}")
def read_preferences(user_id: str, db: Session = Depends(get_db)):
    """Read Preferences"""
    return {"user_id": user_id, "preferences": {}}

@preferences_router.post("/update", response_model=PreferencesResponse, status_code=201)
def post_update_preferences(request: PreferencesUpdateRequest, db: Session = Depends(get_db)):
    """Post Update Preferences"""
    try:
        region, preferences = update_preferences(db, request.user_id, request.updates)
        return {"user_id": request.user_id, "region": region, "preferences": preferences}
    except ValueError as exc:
        _handle_service_errors(exc)
    except Exception as exc:
        _handle_service_errors(exc)
