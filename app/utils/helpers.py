from datetime import datetime, timezone
from typing import Optional, Tuple
import ipaddress

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def format_timestamp(dt: datetime) -> str:
    return dt.isoformat()

def validate_purpose(purpose: str) -> bool:
    valid_purposes = ["analytics", "ads", "email", "location"]
    return purpose.lower() in valid_purposes

def validate_region(region: str) -> bool:
    valid_regions = ["GDPR", "CCPA", "India", "Rest"]
    return region in valid_regions

def detect_region_from_ip(ip: str) -> Tuple[str, str, str]:
    """
    Detect region from IP address.
    Returns: (region, country_name, country_code)
    
    Regions mapping:
    - GDPR: EU countries + UK + EEA countries
    - CCPA: United States (California)
    - India: India
    - Rest: All other countries
    """
    # EU/EEA countries (GDPR)
    gdpr_countries = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
        "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES",
        "SE", "GB", "IS", "LI", "NO"  # UK, Iceland, Liechtenstein, Norway
    }
    
    # For localhost or private IPs, default to Rest
    try:
        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
            return ("Rest", "Unknown", "XX")
    except ValueError:
        # Invalid IP format
        return ("Rest", "Unknown", "XX")
    
    # Try to use a geolocation service
    # Option 1: Use ipapi.co (free tier: 1000 requests/day)
    try:
        import requests
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
        if response.status_code == 200:
            data = response.json()
            
            # Check for errors first
            if "error" in data:
                error_msg = data.get("reason", "Unknown error")
                raise ValueError(f"API error: {error_msg}")
            
            # Try multiple field names for country code
            country_code = (
                data.get("country_code") or 
                data.get("countryCode") or 
                data.get("country") or 
                "XX"
            )
            
            # Try multiple field names for country name
            country_name = (
                data.get("country_name") or 
                data.get("countryName") or 
                data.get("country") or 
                "Unknown"
            )
            
            # Debug logging
            print(f"IP: {ip}, Country Code: {country_code}, Country Name: {country_name}, Full Response: {data}")
            
            # Handle error responses from API
            if country_code == "XX" or not country_code or len(country_code) != 2:
                # If we got an invalid country code, check if there's a region field
                region_code = data.get("region", data.get("region_code", ""))
                if region_code == "EU":
                    print(f"Warning: API returned 'EU' region code for IP {ip}, defaulting to GDPR")
                    return ("GDPR", "European Union", "EU")
                raise ValueError(f"Invalid country code from API: {country_code}")
            
            # Check if API returned region code instead of country code
            # Some APIs return "EU" as a region code - we need to handle this
            if country_code == "EU":
                # If EU region code, we need to check the actual country
                # For now, default to GDPR for EU region
                print(f"Warning: API returned 'EU' as country code for IP {ip}, defaulting to GDPR")
                return ("GDPR", "European Union", "EU")
            
            # Map to regions
            if country_code in gdpr_countries:
                return ("GDPR", country_name, country_code)
            elif country_code == "US":
                return ("CCPA", country_name, country_code)
            elif country_code == "IN":
                return ("India", country_name, country_code)
            else:
                return ("Rest", country_name, country_code)
    except Exception as e:
        print(f"Error calling ipapi.co: {e}")
    
    # Option 2: Fallback to ip-api.com (free tier: 45 requests/minute)
    try:
        import requests
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                country_code = data.get("countryCode", "XX")
                country_name = data.get("country", "Unknown")
                
                # Debug logging
                print(f"IP: {ip}, Country Code: {country_code}, Country Name: {country_name}")
                
                # Map to regions
                if country_code in gdpr_countries:
                    return ("GDPR", country_name, country_code)
                elif country_code == "US":
                    return ("CCPA", country_name, country_code)
                elif country_code == "IN":
                    return ("India", country_name, country_code)
                else:
                    return ("Rest", country_name, country_code)
    except Exception as e:
        print(f"Error calling ip-api.com: {e}")
    
    # Fallback: Simple IP range detection (very basic)
    # This is a simplified approach - for production, use a proper geolocation service
    if ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
        return ("Rest", "Private Network", "XX")
    
    # Default fallback
    return ("Rest", "Unknown", "XX")

