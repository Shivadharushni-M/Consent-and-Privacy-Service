from fastapi import APIRouter, Depends, Query, Request, HTTPException
from typing import Optional
from app.utils.security import api_key_auth
from app.utils.helpers import detect_region_from_ip

router = APIRouter(prefix="/region", tags=["region"], dependencies=[Depends(api_key_auth)])

@router.get("", summary="Get Region", description="Automatically detect region from IP address or use provided IP")
def get_region(
    request: Request,
    ip: Optional[str] = Query(None, description="IP address (optional, will auto-detect if not provided)")
):
    """Get Region - Automatically detects region from client IP or provided IP address"""
    try:
        # Get IP address from request if not provided
        if not ip:
            # Try to get IP from various headers (for proxies/load balancers)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, take the first one
                ip = forwarded_for.split(",")[0].strip()
            else:
                real_ip = request.headers.get("X-Real-IP")
                if real_ip:
                    ip = real_ip
                else:
                    # Fallback to direct client IP
                    client_host = request.client.host if request.client else None
                    if client_host:
                        ip = client_host
                    else:
                        ip = "127.0.0.1"  # Default to localhost if can't detect
            
            # If we detected localhost, try to get the actual public IP
            if ip in ["127.0.0.1", "localhost", "::1"]:
                try:
                    import requests
                    # Try to get the caller's public IP
                    public_ip_response = requests.get("https://api.ipify.org?format=json", timeout=2)
                    if public_ip_response.status_code == 200:
                        public_ip_data = public_ip_response.json()
                        detected_public_ip = public_ip_data.get("ip")
                        if detected_public_ip and detected_public_ip != ip:
                            print(f"Detected localhost ({ip}), using public IP: {detected_public_ip}")
                            ip = detected_public_ip
                except Exception as e:
                    print(f"Could not detect public IP: {e}")
                    # Continue with localhost IP
        
        # Detect region from IP
        region, country, country_code = detect_region_from_ip(ip)
        
        # Ensure we never return "EU" - map it to "GDPR" if somehow returned
        if region == "EU":
            region = "GDPR"
            print(f"Warning: Region was 'EU', mapped to 'GDPR' for IP: {ip}")
        
        # Validate region is one of our expected values
        valid_regions = ["GDPR", "CCPA", "India", "Rest"]
        if region not in valid_regions:
            print(f"Warning: Invalid region '{region}' detected, defaulting to 'Rest'")
            region = "Rest"
        
        return {
            "ip": ip,
            "region": region,
            "country": country,
            "country_code": country_code,
            "detected": True
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in get_region: {e}")
        print(error_details)
        # Return default region on error
        return {
            "ip": ip or "unknown",
            "region": "Rest",
            "country": "Unknown",
            "country_code": "XX",
            "detected": False,
            "error": str(e)
        }
