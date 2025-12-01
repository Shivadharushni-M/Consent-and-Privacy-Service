from typing import Dict
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.consent import PurposeEnum, RegionEnum, StatusEnum


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    user_id: UUID
    region: RegionEnum
    preferences: Dict[PurposeEnum, StatusEnum]


class PreferencesUpdateRequest(BaseModel):
    user_id: UUID
    updates: Dict[PurposeEnum, StatusEnum]

