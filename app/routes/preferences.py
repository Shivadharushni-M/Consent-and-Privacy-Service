from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.preferences import PreferencesResponse, PreferencesUpdateRequest
from app.services.preferences_service import get_latest_preferences, update_preferences
from app.utils.errors import handle_service_error
from app.utils.security import api_key_auth

router = APIRouter(prefix="/consent", tags=["preferences"], dependencies=[Depends(api_key_auth)])


@router.get("/preferences/{user_id}", response_model=PreferencesResponse)
def read_preferences(user_id: UUID, db: Session = Depends(get_db)):
    try:
        region, preferences = get_latest_preferences(db, user_id)
        return PreferencesResponse(user_id=user_id, region=region, preferences=preferences)
    except ValueError as exc:
        handle_service_error(exc)


@router.post("/preferences/update", response_model=PreferencesResponse, status_code=200)
def post_update_preferences(request: PreferencesUpdateRequest, db: Session = Depends(get_db)):
    try:
        region, preferences = update_preferences(db, request.user_id, request.updates)
        return PreferencesResponse(user_id=request.user_id, region=region, preferences=preferences)
    except ValueError as exc:
        handle_service_error(exc)

