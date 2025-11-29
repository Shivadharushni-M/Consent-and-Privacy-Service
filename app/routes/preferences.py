from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.preferences import PreferencesResponse, PreferencesUpdateRequest
from app.services.preferences_service import get_latest_preferences, update_preferences

router = APIRouter(prefix="/consent", tags=["preferences"])

_ERROR_MAP = {
    "user_not_found": (status.HTTP_404_NOT_FOUND, "user_not_found"),
    "invalid_purpose": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_purpose"),
    "invalid_status": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_status"),
    "invalid_region": (status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_region"),
    "no_updates": (status.HTTP_422_UNPROCESSABLE_ENTITY, "no_updates"),
}


def _handle_error(exc: ValueError) -> None:
    status_code, detail = _ERROR_MAP.get(str(exc), (status.HTTP_400_BAD_REQUEST, "invalid_request"))
    raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/preferences/{user_id}", response_model=PreferencesResponse)
def read_preferences(user_id: UUID, db: Session = Depends(get_db)):
    try:
        region, preferences = get_latest_preferences(db, user_id)
        return {"user_id": user_id, "region": region, "preferences": preferences}
    except ValueError as exc:
        _handle_error(exc)


@router.post("/preferences/update", response_model=PreferencesResponse, status_code=status.HTTP_200_OK)
def post_update_preferences(request: PreferencesUpdateRequest, db: Session = Depends(get_db)):
    try:
        region, preferences = update_preferences(db, request.user_id, request.updates)
        return {"user_id": request.user_id, "region": region, "preferences": preferences}
    except ValueError as exc:
        _handle_error(exc)

