from fastapi import APIRouter, Depends, Query, Request
from typing import Optional

from app.schemas.region import RegionResponse
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import validate_region, extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(prefix="/region", tags=["region"], dependencies=[Depends(api_key_auth)])


@router.get("", response_model=RegionResponse, summary="Get Region", description="Automatically detect region from IP address or use provided IP")
def get_region(
    request: Request,
    ip: Optional[str] = Query(None, description="IP address (optional, will auto-detect if not provided)")
) -> RegionResponse:
    """Get Region - Automatically detects region from client IP or provided IP address"""
    # Allow IP to be passed as query parameter for testing/localhost
    if ip:
        ip_address = ip
    else:
        ip_address = extract_client_ip(request)
        # If we got empty string or localhost, try to get public IP
        if not ip_address or ip_address in ["127.0.0.1", "localhost", "::1"]:
            try:
                import requests
                public_ip_response = requests.get("https://api.ipify.org?format=json", timeout=2)
                if public_ip_response.status_code == 200:
                    public_ip_data = public_ip_response.json()
                    detected_public_ip = public_ip_data.get("ip")
                    if detected_public_ip and detected_public_ip != ip_address:
                        ip_address = detected_public_ip
            except Exception:
                pass

    region = detect_region_from_ip(ip_address)
    validated_region = validate_region(region)
    return RegionResponse(region=validated_region)
