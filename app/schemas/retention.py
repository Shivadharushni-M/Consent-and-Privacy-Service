from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.retention import RetentionJobStatusEnum


class RetentionRuleCreate(BaseModel):
    entity_type: str
    retention_period_days: int
    applies_to_region: Optional[str] = None
    applies_to_legal_basis: Optional[str] = None
    tenant_id: Optional[str] = None


class RetentionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: Optional[str] = None
    entity_type: str
    retention_period_days: int
    applies_to_region: Optional[str] = None
    applies_to_legal_basis: Optional[str] = None
    created_at: datetime


class RetentionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: RetentionJobStatusEnum
    deleted_records_count: int
    log: Optional[Dict[str, Any]] = None
