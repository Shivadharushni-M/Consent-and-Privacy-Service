import secrets
from typing import Optional, Union
from uuid import UUID
from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.consent import RegionEnum, User
from app.utils.helpers import validate_region
from app.utils.security import hash_password

_email_adapter = TypeAdapter(EmailStr)


def validate_email(email: str) -> str:
    try:
        return _email_adapter.validate_python(email)
    except ValidationError:
        raise ValueError("invalid_email")


def create_user(db: Session, email: str, region: Union[str, RegionEnum], password: Optional[str] = None) -> User:
    api_key = secrets.token_urlsafe(32)
    password_hash = hash_password(password) if password else None
    user = User(
        email=validate_email(email),
        region=validate_region(region),
        api_key=api_key,
        password_hash=password_hash
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        raise ValueError("duplicate_email")


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise ValueError("user_not_found")
    return user

