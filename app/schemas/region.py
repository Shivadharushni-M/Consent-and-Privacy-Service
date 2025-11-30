from pydantic import BaseModel

from app.models.consent import RegionEnum


class RegionResponse(BaseModel):
    region: RegionEnum

