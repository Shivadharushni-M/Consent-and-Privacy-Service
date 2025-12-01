from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consent import RequestStatusEnum, RequestTypeEnum


# NOTE: This file contains schemas for v1 API endpoints that are currently unused.
# RightsRequestResponse is kept as it may be used when implementing v1 API routes for subject rights requests.
# The following schemas were removed as they are not used anywhere:
# - ExportRequestCreate
# - DeleteRequestCreate
# - VerifyRequest


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
