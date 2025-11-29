from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.consent import (
    PurposeEnum,
    RegionEnum,
    RequestStatusEnum,
    RequestTypeEnum,
    RetentionEntityEnum,
    StatusEnum,
)


class CreateConsentRequest(BaseModel):
    user_id: UUID
    purpose: PurposeEnum
    region: RegionEnum


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    purpose: PurposeEnum
    status: StatusEnum
    region: RegionEnum
    timestamp: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    action: str
    details: Dict[str, Any]
    created_at: datetime


class RetentionScheduleCreate(BaseModel):
    entity_type: RetentionEntityEnum
    retention_days: int = Field(..., gt=0)
    active: bool = True


class RetentionScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: RetentionEntityEnum
    retention_days: int
    active: bool


class SubjectRequestCreate(BaseModel):
    user_id: UUID
    request_type: RequestTypeEnum


class SubjectRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    request_type: RequestTypeEnum
    status: RequestStatusEnum
    requested_at: datetime
    completed_at: Optional[datetime]
