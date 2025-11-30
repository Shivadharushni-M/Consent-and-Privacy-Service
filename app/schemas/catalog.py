from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PurposeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    purpose_group_id: Optional[UUID] = None
    tenant_id: Optional[str] = None


class PurposeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    purpose_group_id: Optional[UUID] = None
    active: Optional[bool] = None


class PurposeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    code: str
    name: str
    description: Optional[str] = None
    purpose_group_id: Optional[UUID] = None
    created_at: datetime
    active: bool


class PurposeGroupCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    precedence: int = 0
    tenant_id: Optional[str] = None


class PurposeGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    code: str
    name: str
    description: Optional[str] = None
    precedence: int
    created_at: datetime


class VendorCreate(BaseModel):
    code: str
    name: str
    relationship_type: Optional[str] = None
    dpa_url: Optional[str] = None
    tenant_id: Optional[str] = None


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    code: str
    name: str
    relationship_type: Optional[str] = None
    dpa_url: Optional[str] = None
    created_at: datetime
