from datetime import datetime, timezone
from typing import Optional

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

