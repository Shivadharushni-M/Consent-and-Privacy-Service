from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.consent import RegionEnum, RequestStatusEnum, RequestTypeEnum
from app.schemas.consent import ConsentResponse


class SubjectRequestIn(BaseModel):
    user_id: UUID
    request_type: RequestTypeEnum
    region: RegionEnum | None = None


class SubjectRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    status: RequestStatusEnum
    request_type: RequestTypeEnum
    verification_token: str | None = None


class DataExportResponse(BaseModel):
    user_id: UUID
    region: RegionEnum
    preferences: Dict[str, str]
    history: List[ConsentResponse]
    audit_logs: List[Dict[str, Any]] = []
    policy_snapshots: List[Dict[str, Any]] = []


class DataAccessResponse(BaseModel):
    user_id: UUID
    email: str
    region: RegionEnum
    purposes: Dict[str, str]


class VerifyTokenRequest(BaseModel):
    token: str
    request_id: UUID

