from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.consent import RegionEnum


class UserCreate(BaseModel):
    email: EmailStr
    region: RegionEnum


class UserUpdate(BaseModel):
    region: RegionEnum | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    region: RegionEnum
    created_at: datetime
    updated_at: datetime

