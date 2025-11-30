from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.consent import PurposeEnum, RegionEnum, StatusEnum


class ConsentCreate(BaseModel):
    subject_external_id: Optional[str] = None
    subject_id: Optional[UUID] = None
    purpose_code: str
    vendor_code: Optional[str] = None
    legal_basis: Optional[str] = None
    status: str
    region_code: str
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    policy_version_id: Optional[UUID] = None
    source: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class ConsentQuery(BaseModel):
    subject_id: Optional[UUID] = None
    subject_external_id: Optional[str] = None
    purpose_code: Optional[str] = None
    vendor_code: Optional[str] = None
    status: Optional[str] = None
    tenant_id: Optional[str] = None


class ConsentRevoke(BaseModel):
    subject_external_id: Optional[str] = None
    subject_id: Optional[UUID] = None
    purpose_code: str
    vendor_code: Optional[str] = None
    reason: Optional[str] = None
    tenant_id: Optional[str] = None


class ConsentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    tenant_id: Optional[str] = None
    subject_id: UUID = Field(alias="user_id")
    purpose: PurposeEnum
    vendor_id: Optional[UUID] = None
    legal_basis: Optional[str] = None
    status: StatusEnum
    region: RegionEnum
    granted_at: Optional[datetime] = None
    valid_from: datetime
    valid_until: Optional[datetime] = None
    timestamp: datetime
    expires_at: Optional[datetime] = None
    policy_version_id: Optional[UUID] = None
    policy_snapshot: Optional[Dict[str, Any]] = None
    source: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
