from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.consent import EventNameEnum


class EventIn(BaseModel):
    user_id: UUID
    event_name: EventNameEnum
    properties: Dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    accepted: bool
    reason: str

