from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from app.models.consent import RegionEnum
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(prefix="/region", tags=["region"], dependencies=[Depends(api_key_auth)])


class RegionResponse(BaseModel):
    ip: str
    region: str
    detected: bool = True


_REGION_NAME_MAP = {
    RegionEnum.EU: "GDPR",
    RegionEnum.US: "CCPA",
    RegionEnum.INDIA: "India",
    RegionEnum.IN: "India",
    RegionEnum.ROW: "Rest",
}


@router.get("", response_model=RegionResponse)
def get_region(request: Request, ip: Optional[str] = Query(None, description="IP address (optional)")):
    if not ip:
        ip = extract_client_ip(request) or "127.0.0.1"
    try:
        detected_region = detect_region_from_ip(ip)
        return RegionResponse(ip=ip, region=_REGION_NAME_MAP.get(detected_region, "Rest"), detected=True)
    except Exception:
        return RegionResponse(ip=ip or "unknown", region="Rest", detected=False)
