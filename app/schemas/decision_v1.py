from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.consent import PurposeEnum, RegionEnum


# NOTE: This file contains schemas for v1 API endpoints that are currently unused.
# DecisionResponse is kept as it may be used when implementing v1 API routes for decision evaluation.
# Note: There's a different DecisionResponse in decision.py that IS currently used.
# The following schema was removed as it is not used anywhere:
# - DecisionRequest


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
