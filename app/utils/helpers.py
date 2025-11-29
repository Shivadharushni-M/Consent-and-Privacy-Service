from datetime import datetime, timezone
from typing import Union

from fastapi import Request

from app.models.consent import PurposeEnum, RegionEnum


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
