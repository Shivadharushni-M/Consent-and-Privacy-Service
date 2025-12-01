from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.consent import RegionEnum


class UserCreate(BaseModel):
    email: EmailStr
    region: RegionEnum | None = Field(
        default=None,
        description="Optional - will auto-detect from IP address if not provided"
    )


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore extra fields instead of forbidding
    
    region: RegionEnum | None = Field(
        default=None,
        description="Optional region value. Valid values: EU, US, INDIA, ROW, IN, BR, SG, AU, JP, CA, UK, ZA, KR"
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    region: RegionEnum
    created_at: datetime
    updated_at: datetime

