from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from app.models.consent import RegionEnum
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import extract_client_ip
from app.utils.security import AuthenticatedActor, get_current_actor

router = APIRouter(prefix="/region", tags=["region"])


class RegionResponse(BaseModel):
    ip: str
    region: str
    detected: bool = True


_REGION_NAME_MAP = {
    RegionEnum.EU: "GDPR",
    RegionEnum.US: "CCPA",
    RegionEnum.INDIA: "India",
    RegionEnum.IN: "India",
    RegionEnum.BR: "LGPD",
    RegionEnum.CA: "PIPEDA",
    RegionEnum.UK: "UK-GDPR",
    RegionEnum.AU: "Australia",
    RegionEnum.JP: "Japan",
    RegionEnum.SG: "Singapore",
    RegionEnum.ZA: "South Africa",
    RegionEnum.KR: "South Korea",
    RegionEnum.ROW: "Rest",
}


@router.get("", response_model=RegionResponse, description="Detect region from IP address. JWT token required (user or admin).")
def get_region(request: Request, ip: Optional[str] = Query(None), actor: AuthenticatedActor = Depends(get_current_actor)):
    input_ip = ip or extract_client_ip(request) or "127.0.0.1"
    detected_region = detect_region_from_ip(input_ip)
    return RegionResponse(ip=input_ip, region=_REGION_NAME_MAP.get(detected_region, "Rest"), detected=detected_region != RegionEnum.ROW)
