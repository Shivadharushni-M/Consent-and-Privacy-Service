from datetime import datetime, timezone
from typing import Dict, Union
from fastapi import Request
from app.models.consent import RegionEnum

_GDPR_REGIONS = {RegionEnum.EU, RegionEnum.INDIA, RegionEnum.UK, RegionEnum.IN}
_LGDP_REGIONS = {RegionEnum.BR}


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_region(region: Union[str, RegionEnum]) -> RegionEnum:
    if isinstance(region, RegionEnum):
        return region
    try:
        return RegionEnum(region)
    except ValueError:
        raise ValueError("invalid_region")


def extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip
    if request.client and request.client.host:
        return request.client.host
    return ""


def build_policy_snapshot(region: Union[str, RegionEnum]) -> Dict[str, Union[str, bool]]:
    region_value = validate_region(region)
    if region_value in _GDPR_REGIONS:
        policy, requires_explicit, default = "gdpr", True, "deny"
    elif region_value in _LGDP_REGIONS:
        policy, requires_explicit, default = "lgpd", True, "deny"
    elif region_value == RegionEnum.US:
        policy, requires_explicit, default = "ccpa", False, "allow"
    else:
        policy, requires_explicit, default = "global", False, "allow"
    return {"region": region_value.value, "policy": policy, "requires_explicit": requires_explicit, "default": default}
