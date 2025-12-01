from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.retention import RetentionEntityTypeEnum, RetentionJobStatusEnum


class RetentionRuleCreate(BaseModel):
    entity_type: RetentionEntityTypeEnum = Field(
        ...,
        description="Type of entity to apply retention to. Valid values: ConsentRecord, AuditLogEntry, RightsRequest",
        examples=[RetentionEntityTypeEnum.CONSENT_RECORD]
    )
    retention_period_days: int = Field(
        ...,
        description="Number of days to retain data before deletion",
        examples=[365],
        gt=0
    )
    applies_to_region: Optional[str] = Field(
        None,
        description="Optional region code to filter which records this rule applies to (e.g., 'EU', 'US')",
        examples=["EU"]
    )
    applies_to_legal_basis: Optional[str] = Field(
        None,
        description="Optional legal basis to filter which records this rule applies to",
        examples=["consent"]
    )
    tenant_id: Optional[str] = Field(
        None,
        description="Optional tenant ID for multi-tenant scenarios",
        examples=["tenant-123"]
    )


class RetentionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier for the retention rule")
    tenant_id: Optional[str] = Field(None, description="Tenant ID if applicable")
    entity_type: RetentionEntityTypeEnum = Field(..., description="Type of entity this rule applies to")
    retention_period_days: int = Field(..., description="Number of days to retain data")
    applies_to_region: Optional[str] = Field(None, description="Region code filter if applicable")
    applies_to_legal_basis: Optional[str] = Field(None, description="Legal basis filter if applicable")
    created_at: datetime = Field(..., description="Timestamp when the rule was created")


class RetentionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier for the retention job")
    started_at: datetime = Field(..., description="Timestamp when the job started")
    finished_at: Optional[datetime] = Field(None, description="Timestamp when the job finished (null if still running)")
    status: RetentionJobStatusEnum = Field(..., description="Current status of the job: running, completed, or failed")
    deleted_records_count: int = Field(..., description="Number of records deleted by this job")
    log: Optional[Dict[str, Any]] = Field(None, description="Optional log data with job execution details")
