from fastapi import APIRouter, Request

from app.schemas.region import RegionResponse
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import validate_region

router = APIRouter(prefix="/region", tags=["region"])


@router.get("", response_model=RegionResponse)
def get_region(request: Request) -> RegionResponse:
    ip_address = _extract_client_ip(request)
    region = detect_region_from_ip(ip_address)
    validated_region = validate_region(region)
    return RegionResponse(region=validated_region)


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    if request.client and request.client.host:
        return request.client.host

    return ""

