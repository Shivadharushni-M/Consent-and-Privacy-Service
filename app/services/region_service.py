from __future__ import annotations

from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Optional, Sequence, Tuple

from app.config import settings
from app.models.consent import RegionEnum

try:  # pragma: no cover - optional dependency
    from geoip2.database import Reader
except ImportError:  # pragma: no cover - optional dependency
    Reader = None  # type: ignore


GEOIP_DB_PATH = Path(__file__).resolve().parent.parent / "geoip" / "GeoLite2-Country.mmdb"
_MAXMIND_READY = bool(settings.MAXMIND_ACCOUNT_ID and settings.MAXMIND_LICENSE_KEY)
_GEOIP_READER: Optional["Reader"] = None

if _MAXMIND_READY and Reader is not None:
    try:
        if GEOIP_DB_PATH.exists():
            _GEOIP_READER = Reader(str(GEOIP_DB_PATH))
    except Exception:
        _GEOIP_READER = None


EU_COUNTRIES: frozenset[str] = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "CH",
        "CY",
        "CZ",
        "DE",
        "DK",
        "EE",
        "ES",
        "FI",
        "FR",
        "GR",
        "HR",
        "HU",
        "IE",
        "IT",
        "LT",
        "LU",
        "LV",
        "MT",
        "NL",
        "NO",
        "PL",
        "PT",
        "RO",
        "SE",
        "SI",
        "SK",
    }
)

LIGHTWEIGHT_IP_RANGES: Sequence[Tuple[str, str]] = (
    ("2.16.0.0/12", "FR"),  # EU sample (Akamai range covering several EU states)
    ("8.0.0.0/7", "US"),  # US-based Google ranges
    ("49.32.0.0/11", "IN"),  # India broadband allocations
)

_PREPARED_RANGES = tuple((ip_network(cidr), iso) for cidr, iso in LIGHTWEIGHT_IP_RANGES)


def detect_region_from_ip(ip: Optional[str]) -> RegionEnum:
    """
    Determine the user's region based on IP address.

    Always falls back to mock detection (ROW) to avoid raising exceptions.
    """

    normalized_ip = (ip or "").strip()

    if _is_local_ip(normalized_ip):
        return RegionEnum.ROW

    maxmind_region = _detect_with_maxmind(normalized_ip)
    if maxmind_region is not None:
        return maxmind_region

    return _lightweight_region(normalized_ip)


def _detect_with_maxmind(ip: str) -> Optional[RegionEnum]:
    if not ip or _GEOIP_READER is None:
        return None

    try:
        response = _GEOIP_READER.country(ip)
        iso_code = (response.country.iso_code or "").upper()
    except Exception:
        return None

    if not iso_code:
        return None

    return _map_iso_to_region(iso_code)


def _lightweight_region(ip: str) -> RegionEnum:
    iso_code = _lookup_iso_from_ip(ip)
    return _map_iso_to_region(iso_code)


def _lookup_iso_from_ip(ip: str) -> Optional[str]:
    if not ip:
        return None
    try:
        parsed_ip = ip_address(ip)
    except ValueError:
        return None

    for network, iso_code in _PREPARED_RANGES:
        if parsed_ip.version != network.version:
            continue
        if parsed_ip in network:
            return iso_code
    return None


def _map_iso_to_region(iso_code: Optional[str]) -> RegionEnum:
    if not iso_code:
        return RegionEnum.ROW

    normalized_iso = iso_code.upper()
    if normalized_iso == "US":
        return RegionEnum.US
    if normalized_iso == "IN":
        return RegionEnum.INDIA
    if normalized_iso in EU_COUNTRIES:
        return RegionEnum.EU
    return RegionEnum.ROW


def _is_local_ip(ip: str) -> bool:
    if not ip:
        return True
    normalized = ip.lower()
    return normalized.startswith("127.") or normalized.startswith("localhost") or normalized == "::1"

