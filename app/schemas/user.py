from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.consent import RegionEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str | None = Field(
        default=None,
        description="Optional - if not provided, user will need to set password later or use API key for login"
    )
    region: RegionEnum | None = Field(
        default=None,
        description="Optional - will auto-detect from IP address if not provided"
    )


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    region: RegionEnum
    created_at: datetime
    updated_at: datetime


class UserCreateResponse(BaseModel):
    """Response model for user creation. Includes api_key which is shown only once."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    region: RegionEnum
    api_key: str = Field(..., description="API key for user authentication. Store this securely - it is shown only once.")
    created_at: datetime
    updated_at: datetime

