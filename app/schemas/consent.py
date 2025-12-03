from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.consent import PurposeEnum, RegionEnum, StatusEnum


class CreateConsentRequest(BaseModel):
    user_id: UUID
    purpose: PurposeEnum
    region: RegionEnum
    expires_at: Optional[datetime] = None
    expires_in_days: Optional[int] = Field(None, gt=0, description="Number of days until consent expires")
    policy_snapshot: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_expiry(self):
        if self.expires_at and self.expires_in_days:
            raise ValueError("Cannot specify both 'expires_at' and 'expires_in_days'. Please provide only one:\n- Use 'expires_at' to set a specific expiration date/time\n- Use 'expires_in_days' to set expiration relative to now (e.g., expires_in_days: 1)")
        return self

    def get_expires_at(self) -> Optional[datetime]:
        if self.expires_at:
            return self.expires_at
        if self.expires_in_days:
            from app.utils.helpers import get_utc_now
            return get_utc_now() + timedelta(days=self.expires_in_days)
        return None


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    purpose: PurposeEnum
    status: StatusEnum
    region: RegionEnum
    timestamp: datetime
    expires_at: Optional[datetime] = None
    policy_snapshot: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    policy_snapshot: Optional[Dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def handle_none_details(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("details") is None:
            data["details"] = {}
        elif hasattr(data, "details") and data.details is None:
            data.details = {}
        return data


