from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


def _handle_service_error(exc: ValueError) -> None:
    error_map = {
        "invalid_email": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid email"),
        "invalid_region": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid region"),
        "duplicate_email": (status.HTTP_409_CONFLICT, "Email already exists"),
        "user_not_found": (status.HTTP_404_NOT_FOUND, "User not found"),
    }
    detail = error_map.get(str(exc), (status.HTTP_400_BAD_REQUEST, "Invalid request"))
    raise HTTPException(status_code=detail[0], detail=detail[1]) from exc


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return user_service.create_user(db=db, email=user.email, region=user.region)
    except ValueError as exc:
        _handle_service_error(exc)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    try:
        return user_service.get_user(db=db, user_id=user_id)
    except ValueError as exc:
        _handle_service_error(exc)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, payload: UserUpdate, db: Session = Depends(get_db)):
    if payload.region is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Region is required"
        )
    try:
        return user_service.update_region(db=db, user_id=user_id, region=payload.region)
    except ValueError as exc:
        _handle_service_error(exc)

