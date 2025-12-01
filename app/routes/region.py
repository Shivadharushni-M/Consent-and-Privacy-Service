from fastapi import APIRouter, Depends, Query, Request
from typing import Optional
from pydantic import BaseModel
from app.utils.security import api_key_auth
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import extract_client_ip
from app.models.consent import RegionEnum

router = APIRouter(prefix="/region", tags=["region"], dependencies=[Depends(api_key_auth)])

class RegionResponse(BaseModel):
    """Region response with mapped region names"""
    ip: str
    region: str  # GDPR, CCPA, India, or Rest
    detected: bool = True

def _map_region_enum_to_region_name(region_enum: RegionEnum) -> str:
    """Map RegionEnum to expected region names"""
    mapping = {
        RegionEnum.EU: "GDPR",
        RegionEnum.US: "CCPA",
        RegionEnum.INDIA: "India",
        RegionEnum.IN: "India",
        RegionEnum.ROW: "Rest",
    }
    # For any other RegionEnum values, default to Rest
    return mapping.get(region_enum, "Rest")

@router.get("", response_model=RegionResponse, summary="Get Region", description="Automatically detect region from IP address or use provided IP")
def get_region(
    request: Request,
    ip: Optional[str] = Query(None, description="IP address (optional, will auto-detect if not provided)")
):
    """Get Region - Automatically detects region from client IP or provided IP address"""
    try:
        # Get IP address from request if not provided
        if not ip:
            ip = extract_client_ip(request)
            if not ip:
                ip = "127.0.0.1"  # Default to localhost if can't detect
        
        # Detect region from IP (region_service handles localhost -> public IP conversion)
        detected_region_enum = detect_region_from_ip(ip)
        
        # Map RegionEnum to expected region name (GDPR, CCPA, India, Rest)
        region_name = _map_region_enum_to_region_name(detected_region_enum)
        
        return RegionResponse(
            ip=ip,
            region=region_name,
            detected=True
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_region: {e}")
        print(error_details)
        # Return default region on error
        return RegionResponse(
            ip=ip or "unknown",
            region="Rest",
            detected=False
        )
