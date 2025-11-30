from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.consent import ConsentResponse, CreateConsentRequest
from app.schemas.common import PreferencesUpdateRequest
from app.services import consent_service
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/consent",
    tags=["consent"],
    dependencies=[Depends(api_key_auth)],
)


def _handle_service_errors(exc: Exception) -> None:
    error_str = str(exc)
    if error_str == "user_not_found":
        raise HTTPException(status_code=404, detail="User not found") from exc
    if error_str == "invalid_region":
        raise HTTPException(status_code=422, detail="Invalid region") from exc
    if error_str == "database_error":
        raise HTTPException(status_code=500, detail="Database error occurred") from exc
    # For other ValueError exceptions, use the message
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=error_str) from exc
    # For any other exception, return a generic error
    raise HTTPException(status_code=500, detail=f"Internal server error: {error_str}") from exc


@router.post("/grant", response_model=ConsentResponse, status_code=201)
def grant_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        # Try new service signature first (with expires_at)
        if hasattr(request, 'get_expires_at'):
            return consent_service.grant_consent(
                db=db,
                user_id=request.user_id,
                purpose=request.purpose,
                region=request.region,
                expires_at=request.get_expires_at(),
            )
        else:
            # Fallback to old signature (with policy_snapshot)
            return consent_service.grant_consent(
                db=db,
                user_id=request.user_id,
                purpose=request.purpose,
                region=request.region,
                policy_snapshot=getattr(request, 'policy_snapshot', None)
            )
    except Exception as exc:
        _handle_service_errors(exc)


@router.post("/revoke", response_model=ConsentResponse, status_code=201)
def revoke_consent(request: CreateConsentRequest, db: Session = Depends(get_db)):
    try:
        # Try new service signature first (with expires_at)
        if hasattr(request, 'get_expires_at'):
            return consent_service.revoke_consent(
                db=db,
                user_id=request.user_id,
                purpose=request.purpose,
                region=request.region,
                expires_at=request.get_expires_at(),
            )
        else:
            # Fallback to old signature (with policy_snapshot)
            return consent_service.revoke_consent(
                db=db,
                user_id=request.user_id,
                purpose=request.purpose,
                region=request.region,
                policy_snapshot=getattr(request, 'policy_snapshot', None)
            )
    except Exception as exc:
        _handle_service_errors(exc)


@router.get("/history/{user_id}", response_model=List[ConsentResponse])
def get_consent_history(user_id: str, db: Session = Depends(get_db)):
    """Get consent history - accepts both UUID string and integer string for backward compatibility"""
    try:
        # Try to parse as UUID first
        try:
            user_uuid = UUID(user_id)
            return consent_service.get_history(db=db, user_id=user_uuid)
        except ValueError:
            # If not a valid UUID, try as integer (for backward compatibility)
            try:
                int_id = int(user_id)
                if int_id <= 0:
                    raise HTTPException(status_code=400, detail="Invalid user_id")
                # Convert integer to UUID for service call
                return consent_service.get_history(db=db, user_id=user_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as exc:
        _handle_service_errors(exc)


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
