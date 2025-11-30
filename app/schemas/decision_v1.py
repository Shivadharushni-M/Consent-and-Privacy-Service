from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.consent import PurposeEnum, RegionEnum


class DecisionRequest(BaseModel):
    subject_external_id: Optional[str] = None
    subject_id: Optional[UUID] = None
    purpose_code: str
    vendor_code: Optional[str] = None
    region_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    tenant_id: Optional[str] = None


class DecisionResponse(BaseModel):
    allowed: bool
    decision: str
    legal_basis: Optional[str] = None
    source: Optional[str] = None
    policy_version_id: Optional[UUID] = None
    consent_record_id: Optional[UUID] = None
    reasoning: List[str]
    evidence: Optional[Dict[str, Any]] = None
    effective_at: datetime
