from typing import Union
from uuid import UUID

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.consent import RegionEnum, User
from app.utils.helpers import validate_region


_email_adapter = TypeAdapter(EmailStr)


def validate_email(email: str) -> str:
    try:
        return _email_adapter.validate_python(email)
    except ValidationError as exc:
        raise ValueError("invalid_email") from exc


def create_user(db: Session, email: str, region: Union[str, RegionEnum]) -> User:
    email_value = validate_email(email)
    region_value = validate_region(region)

    user = User(email=email_value, region=region_value)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("duplicate_email") from exc


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise ValueError("user_not_found")
    return user


def update_region(db: Session, user_id: UUID, region: Union[str, RegionEnum]) -> User:
    user = get_user(db, user_id)
    user.region = validate_region(region)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

