from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.consent import RegionEnum, RequestStatusEnum, RequestTypeEnum
from app.schemas.consent import ConsentResponse


class SubjectRequestIn(BaseModel):
    user_id: UUID
    request_type: RequestTypeEnum
    new_email: EmailStr | None = None
    new_region: RegionEnum | None = None


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


class DataAccessResponse(BaseModel):
    """Simplified response for GDPR Right of Access - view data only."""
    user_id: UUID
    email: str
    region: RegionEnum
    purposes: Dict[str, str]  # purpose -> status mapping


