from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurposeCreate(BaseModel):
    code: str = Field(..., description="Unique code identifier for the purpose (e.g., 'analytics', 'marketing')", example="analytics")
    name: str = Field(..., description="Display name of the purpose", example="Analytics")
    description: Optional[str] = Field(None, description="Detailed description of the purpose", example="Collect and analyze user behavior data")
    purpose_group_id: Optional[UUID] = Field(None, description="UUID of the purpose group this purpose belongs to (must be a valid UUID format, e.g., '123e4567-e89b-12d3-a456-426614174000'). Get the UUID from the purpose group's 'id' field when listing purpose groups.", example="123e4567-e89b-12d3-a456-426614174000")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant support", example="tenant-123")


class PurposeUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Display name of the purpose", example="Analytics & Tracking")
    description: Optional[str] = Field(None, description="Detailed description of the purpose", example="Collect and analyze user behavior data for product improvement")
    purpose_group_id: Optional[UUID] = Field(None, description="UUID of the purpose group this purpose belongs to (must be a valid UUID format, e.g., '123e4567-e89b-12d3-a456-426614174000'). Get the UUID from the purpose group's 'id' field when listing purpose groups.", example="123e4567-e89b-12d3-a456-426614174000")
    active: Optional[bool] = Field(None, description="Whether the purpose is active", example=True)


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
    code: str = Field(..., description="Unique code identifier for the purpose group (e.g., 'essential', 'functional')", example="essential")
    name: str = Field(..., description="Display name of the purpose group", example="Essential Purposes")
    description: Optional[str] = Field(None, description="Detailed description of the purpose group", example="Purposes essential for the service to function")
    precedence: int = Field(0, description="Ordering precedence (lower numbers appear first)", example=1)
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant support", example="tenant-123")


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
    code: str = Field(..., description="Unique code identifier for the vendor (e.g., 'google-analytics', 'facebook-pixel')", example="google-analytics")
    name: str = Field(..., description="Display name of the vendor", example="Google Analytics")
    relationship_type: Optional[str] = Field(None, description="Type of relationship (e.g., 'processor', 'controller', 'third-party')", example="processor")
    dpa_url: Optional[str] = Field(None, description="URL to the Data Processing Agreement", example="https://example.com/dpa/google-analytics")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant support", example="tenant-123")


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    code: str
    name: str
    relationship_type: Optional[str] = None
    dpa_url: Optional[str] = None
    created_at: datetime
