from typing import Dict, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.consent import RegionEnum, RequestStatusEnum, RequestTypeEnum
from app.schemas.consent import ConsentResponse


class SubjectRequestIn(BaseModel):
    user_id: UUID
    request_type: RequestTypeEnum


class SubjectRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: UUID
    status: RequestStatusEnum
    request_type: RequestTypeEnum


class DataExportResponse(BaseModel):
    user_id: UUID
    region: RegionEnum
    preferences: Dict[str, str]
    history: List[ConsentResponse]


