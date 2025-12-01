from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.consent import RegionEnum


# NOTE: This file contains schemas for v1 API endpoints that are currently unused.
# SubjectResponse is kept as it may be used when implementing v1 API routes for subject management.
# The following schemas were removed as they are not used anywhere:
# - SubjectCreate
# - SubjectUpdate


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
