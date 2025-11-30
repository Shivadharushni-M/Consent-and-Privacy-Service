from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consent import RequestStatusEnum, RequestTypeEnum


class ExportRequestCreate(BaseModel):
    subject_external_id: Optional[str] = Field(None, description="External identifier for the subject (e.g., 'user-123')")
    subject_id: Optional[UUID] = Field(None, description="Internal UUID of the subject")
    notification_channel: Optional[Dict[str, str]] = Field(None, description="Notification channel details (e.g., {'type': 'email', 'value': 'user@example.com'})")
    callback_url: Optional[str] = Field(None, description="Optional callback URL for webhook notifications")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant systems")
    
    @model_validator(mode='after')
    def validate_subject_identifier(self):
        """Ensure at least one subject identifier is provided."""
        if not self.subject_id and not self.subject_external_id:
            raise ValueError("At least one of 'subject_id' or 'subject_external_id' must be provided")
        return self


class DeleteRequestCreate(BaseModel):
    subject_external_id: Optional[str] = Field(None, description="External identifier for the subject (e.g., 'user-123')")
    subject_id: Optional[UUID] = Field(None, description="Internal UUID of the subject")
    notification_channel: Optional[Dict[str, str]] = Field(None, description="Notification channel details (e.g., {'type': 'email', 'value': 'user@example.com'})")
    callback_url: Optional[str] = Field(None, description="Optional callback URL for webhook notifications")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier for multi-tenant systems")
    
    @model_validator(mode='after')
    def validate_subject_identifier(self):
        """Ensure at least one subject identifier is provided."""
        if not self.subject_id and not self.subject_external_id:
            raise ValueError("At least one of 'subject_id' or 'subject_external_id' must be provided")
        return self


class VerifyRequest(BaseModel):
    token: str


class RightsRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    subject_id: UUID
    type: RequestTypeEnum
    status: RequestStatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    verification_token_id: Optional[UUID] = None
    verification_token: Optional[str] = Field(None, description="Verification token to use in /verify endpoint")
    result_location: Optional[str] = None
    error_message: Optional[str] = None
    requested_by: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def map_model_fields(cls, data: Any) -> Any:
        """Map SubjectRequest model fields to response schema fields"""
        if hasattr(data, 'user_id'):
            # It's a model instance
            return {
                'id': data.id,
                'tenant_id': data.tenant_id,
                'subject_id': data.user_id,
                'type': data.request_type,
                'status': data.status,
                'created_at': data.requested_at,
                'updated_at': data.completed_at,
                'verification_token_id': data.verification_token_id,
                'result_location': data.result_location,
                'error_message': data.error_message,
                'requested_by': data.requested_by,
            }
        return data
