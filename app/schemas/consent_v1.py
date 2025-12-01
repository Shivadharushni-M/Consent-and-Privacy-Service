from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.consent import PurposeEnum, RegionEnum, StatusEnum


# NOTE: This file contains schemas for v1 API endpoints that are currently unused.
# ConsentRecordResponse is kept as it may be used when implementing v1 API routes for consent management.
# The following schemas were removed as they are not used anywhere:
# - ConsentCreate
# - ConsentQuery  
# - ConsentRevoke


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
