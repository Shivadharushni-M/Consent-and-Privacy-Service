from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.consent import RegionEnum


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    region_code: str
    tenant_id: Optional[str] = None


class PolicyVersionCreate(BaseModel):
    effective_from: datetime
    effective_to: Optional[datetime] = None
    matrix: Dict[str, Any]
    created_by: Optional[str] = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    region_code: RegionEnum
    created_at: datetime
    current_version_id: Optional[UUID] = None


class PolicyVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_id: UUID
    version_number: int
    effective_from: datetime
    effective_to: Optional[datetime] = None
    matrix: Dict[str, Any]
    created_at: datetime
    created_by: Optional[str] = None


class PolicySnapshotQuery(BaseModel):
    region_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    tenant_id: Optional[str] = None
