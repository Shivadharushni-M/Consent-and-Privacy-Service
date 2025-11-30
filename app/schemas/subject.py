from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.consent import RegionEnum


class SubjectCreate(BaseModel):
    external_id: Optional[str] = None
    identifier_type: Optional[str] = None
    identifier_value: Optional[str] = None
    region_code: Optional[RegionEnum] = None
    tenant_id: Optional[str] = None


class SubjectUpdate(BaseModel):
    identifier_type: Optional[str] = None
    identifier_value: Optional[str] = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: Optional[str] = None
    tenant_id: Optional[str] = None
    email: str
    primary_identifier_type: Optional[str] = None
    primary_identifier_value: Optional[str] = None
    region: RegionEnum
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
