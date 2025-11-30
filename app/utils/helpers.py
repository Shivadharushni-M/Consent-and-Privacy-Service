from datetime import datetime, timezone
from typing import Dict, Union, Optional

from fastapi import Request

from app.models.consent import PurposeEnum, RegionEnum


_GDPR_REGIONS = {RegionEnum.EU, RegionEnum.INDIA, RegionEnum.UK, RegionEnum.IN}
_LGDP_REGIONS = {RegionEnum.BR}

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    return dt.isoformat()


def validate_purpose(purpose: Union[str, PurposeEnum]) -> PurposeEnum:
    if isinstance(purpose, PurposeEnum):
        return purpose
    try:
        return PurposeEnum(purpose)
    except ValueError as exc:
        raise ValueError("invalid_purpose") from exc


def validate_region(region: Union[str, RegionEnum]) -> RegionEnum:
    if isinstance(region, RegionEnum):
        return region
    try:
        return RegionEnum(region)
    except ValueError as exc:
        raise ValueError("invalid_region") from exc


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
        policy = "gdpr"
        requires_explicit = True
        default = "deny"
    elif region_value in _LGDP_REGIONS:
        policy = "lgpd"
        requires_explicit = True
        default = "deny"
    elif region_value == RegionEnum.US:
        policy = "ccpa"
        requires_explicit = False
        default = "allow"
    else:
        policy = "global"
        requires_explicit = False
        default = "allow"

    return {
        "region": region_value.value,
        "policy": policy,
        "requires_explicit": requires_explicit,
        "default": default,
    }
