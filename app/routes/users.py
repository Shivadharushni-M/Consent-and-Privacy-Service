from uuid import UUID
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services import user_service
from app.services.region_service import detect_region_from_ip
from app.utils.errors import handle_service_error
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(api_key_auth)])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    try:
        if user.region is None:
            user.region = detect_region_from_ip(extract_client_ip(request))
        return user_service.create_user(db=db, email=user.email, region=user.region)
    except ValueError as exc:
        handle_service_error(exc)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    try:
        return user_service.get_user(db=db, user_id=user_id)
    except ValueError as exc:
        handle_service_error(exc)
