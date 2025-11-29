from uuid import UUID

from pydantic import BaseModel

from app.models.consent import PurposeEnum, RegionEnum


class DecisionResponse(BaseModel):
    user_id: UUID
    purpose: PurposeEnum
    region: RegionEnum
    allowed: bool
    reason: str

