from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import UserCreate, UserCreateResponse, UserResponse
from app.services import user_service
from app.services.region_service import detect_region_from_ip
from app.utils.errors import handle_service_error
from app.utils.helpers import extract_client_ip
from app.utils.security import AuthenticatedActor, get_current_actor, get_optional_actor, Actor

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserCreateResponse,
    status_code=201,
    description="Create a new user. Returns an API key that should be stored securely - it is shown only once. Admin or User JWT token, or no auth (self-registration) allowed."
)
def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db), actor: Optional[Actor] = Depends(get_optional_actor)):
    try:
        if user.region is None:
            user.region = detect_region_from_ip(extract_client_ip(request))
        created_user = user_service.create_user(db=db, email=user.email, region=user.region, password=user.password)
        return UserCreateResponse(id=created_user.id, email=created_user.email, region=created_user.region, api_key=created_user.api_key, created_at=created_user.created_at, updated_at=created_user.updated_at)
    except ValueError as exc:
        handle_service_error(exc)


@router.get("/{user_id}", response_model=UserResponse, description="Get user details. Admin JWT token required.")
def get_user(user_id: UUID, db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(get_current_actor)):
    try:
        return user_service.get_user(db=db, user_id=user_id)
    except ValueError as exc:
        handle_service_error(exc)
