from typing import Dict
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.models.consent import PurposeEnum, RegionEnum, StatusEnum


class PreferencesResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    user_id: UUID
    region: RegionEnum
    preferences: Dict[PurposeEnum, StatusEnum]


class PreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "a333a45d-3450-4e02-857b-b282a0350b0a",
                "updates": {
                    "analytics": "granted",
                    "ads": "granted",
                    "email": "denied"
                }
            }
        }
    )
    
    user_id: UUID
    updates: Dict[PurposeEnum, StatusEnum] = Field(
        ...,
        description="Dictionary mapping purpose to status. Valid purposes: analytics, ads, email, location, marketing, personalization, data_sharing. Valid statuses: granted, denied, revoked, withdrawn, expired."
    )

