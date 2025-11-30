from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consent import (
    PurposeEnum,
    RegionEnum,
    RequestStatusEnum,
    RequestTypeEnum,
    RetentionEntityEnum,
    StatusEnum,
)


class CreateConsentRequest(BaseModel):
    """Create consent request - supports both new (UUID/enums) and old (int/str) formats for backward compatibility"""
    user_id: Union[UUID, int, str] = Field(..., description="User ID (UUID, integer, or UUID string)")
    purpose: Union[PurposeEnum, str] = Field(..., description="Purpose (enum or string)")
    region: Union[RegionEnum, str] = Field(..., description="Region (enum or string)")
    expires_at: Optional[datetime] = None
    expires_in_days: Optional[int] = Field(None, gt=0, description="Number of days until consent expires")
    policy_snapshot: Optional[Dict[str, Any]] = None  # For backward compatibility

    @model_validator(mode="after")
    def validate_expiry(self):
        """Ensure only one expiry method is provided."""
        if self.expires_at and self.expires_in_days:
            raise ValueError("Cannot specify both expires_at and expires_in_days")
        return self

    def get_expires_at(self) -> Optional[datetime]:
        """Calculate expires_at from expires_in_days if provided."""
        if self.expires_at:
            return self.expires_at
        if self.expires_in_days:
            from app.utils.helpers import get_utc_now
            return get_utc_now() + timedelta(days=self.expires_in_days)
        return None


class ConsentResponse(BaseModel):
    """Consent response - supports both new and old model structures"""
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, int]  # Support both UUID and int for backward compatibility
    user_id: Union[UUID, int, str]  # Support UUID, int, or string
    purpose: Union[PurposeEnum, str]  # Support enum or string
    status: Union[StatusEnum, str]  # Support enum or string
    region: Union[RegionEnum, str]  # Support enum or string
    timestamp: datetime
    expires_at: Optional[datetime] = None
    policy_snapshot: Optional[Dict[str, Any]] = None


class AuditLogResponse(BaseModel):
    """Audit log response"""
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, int]  # Support both UUID and int
    user_id: Optional[Union[UUID, int]] = None
    action: str
    details: Optional[Dict[str, Any]] = None  # Optional for backward compatibility
    created_at: Optional[datetime] = None
    timestamp: Optional[datetime] = None  # Legacy field
    policy_snapshot: Optional[Dict[str, Any]] = None


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
