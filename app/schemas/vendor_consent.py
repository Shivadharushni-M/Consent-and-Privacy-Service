from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.consent import PurposeEnum, RegionEnum, StatusEnum, VendorEnum


class CreateVendorConsentRequest(BaseModel):
    user_id: UUID
    vendor: VendorEnum
    purpose: PurposeEnum
    region: RegionEnum
    expires_at: Optional[datetime] = None


class VendorConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    vendor: VendorEnum
    purpose: PurposeEnum
    status: StatusEnum
    region: RegionEnum
    timestamp: datetime
    expires_at: Optional[datetime] = None
    policy_snapshot: Optional[Dict[str, Any]] = None

