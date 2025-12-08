from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.preferences import PreferencesResponse, PreferencesUpdateRequest
from app.services.preferences_service import get_latest_preferences, update_preferences
from app.utils.errors import handle_service_error
from app.utils.security import AuthenticatedActor, get_current_actor, validate_user_action

router = APIRouter(prefix="/consent", tags=["preferences"])


@router.get(
    "/preferences/{user_id}",
    response_model=PreferencesResponse,
    description="Get user preferences. User JWT token required - users can only view their own preferences."
)
def read_preferences(user_id: UUID, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    try:
        validate_user_action(actor, user_id)
        region, preferences = get_latest_preferences(db, user_id)
        return PreferencesResponse(user_id=user_id, region=region, preferences=preferences)
    except ValueError as exc:
        handle_service_error(exc)


@router.post(
    "/preferences/update",
    response_model=PreferencesResponse,
    status_code=200,
    description="Update user preferences. User JWT token required - users can only update their own preferences."
)
def post_update_preferences(request: PreferencesUpdateRequest, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    try:
        validate_user_action(actor, request.user_id)
        region, preferences = update_preferences(db, request.user_id, request.updates, actor=actor)
        return PreferencesResponse(user_id=request.user_id, region=region, preferences=preferences)
    except ValueError as exc:
        handle_service_error(exc)

