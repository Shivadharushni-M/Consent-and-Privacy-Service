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
    # India IP ranges - CHECK FIRST to avoid conflicts with US ranges
    ("14.0.0.0/8", "IN"),  # India IP ranges
    ("27.0.0.0/8", "IN"),  # India IP ranges
    ("49.32.0.0/11", "IN"),  # India broadband allocations
    ("59.0.0.0/8", "IN"),  # India IP ranges
    ("103.0.0.0/8", "IN"),  # India IP ranges (common ISPs - Jio, Airtel, BSNL)
    ("106.0.0.0/8", "IN"),  # India IP ranges
    ("115.0.0.0/8", "IN"),  # India IP ranges
    ("117.0.0.0/8", "IN"),  # India IP ranges (BSNL, Airtel)
    ("122.0.0.0/8", "IN"),  # India IP ranges (Jio, Airtel, BSNL)
    ("180.0.0.0/8", "IN"),  # India IP ranges
    ("182.0.0.0/8", "IN"),  # India IP ranges
    ("183.0.0.0/8", "IN"),  # India IP ranges
    ("223.0.0.0/8", "IN"),  # India IP ranges
    # EU IP ranges
    ("2.16.0.0/12", "FR"),  # EU sample (Akamai range covering several EU states)
    ("37.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("80.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("84.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("85.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("87.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("91.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("94.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("145.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("185.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("194.0.0.0/8", "NL"),  # Netherlands IP ranges
    ("212.0.0.0/8", "NL"),  # Netherlands IP ranges
    # US IP ranges - CHECK LAST as it's very broad
    ("8.0.0.0/7", "US"),  # US-based Google ranges (very broad, check last)
)

_PREPARED_RANGES = tuple((ip_network(cidr), iso) for cidr, iso in LIGHTWEIGHT_IP_RANGES)


def detect_region_from_ip(ip: Optional[str]) -> RegionEnum:
    """Determine the user's region based on IP address."""
    normalized_ip = (ip or "").strip()
    if _is_local_ip(normalized_ip):
        public_ip = _get_public_ip()
        normalized_ip = public_ip if public_ip and not _is_local_ip(public_ip) else ""
    if not normalized_ip:
        return RegionEnum.ROW
    result = _lightweight_region(normalized_ip)
    if result != RegionEnum.ROW:
        return result
    maxmind_result = _detect_with_maxmind(normalized_ip)
    return maxmind_result if maxmind_result and maxmind_result != RegionEnum.ROW else RegionEnum.ROW


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
    """Check if IP is localhost or private network."""
    if not ip:
        return True
    normalized = ip.lower()
    return normalized.startswith(("127.", "localhost", "192.168.", "10.", "172.16.")) or normalized == "::1"


def _get_public_ip() -> Optional[str]:
    """
    Attempt to fetch the user's public IP address.
    Falls back gracefully if the service is unavailable.
    """
    try:
        import httpx
        # Try multiple services for reliability
        services = [
            ("https://api.ipify.org?format=json", "json"),
            ("https://api64.ipify.org?format=json", "json"),
            ("https://icanhazip.com", "text"),
        ]
        
        for service_url, response_type in services:
            try:
                with httpx.Client(timeout=3.0) as client:
                    response = client.get(service_url)
                    response.raise_for_status()
                    if response_type == "json":
                        ip = response.json().get("ip", "").strip()
                    else:
                        ip = response.text.strip()
                    if ip and not _is_local_ip(ip):
                        return ip
            except Exception:
                continue
    except ImportError:
        # httpx not available, try urllib as fallback
        try:
            import urllib.request
            import json
            with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=3) as response:
                data = json.loads(response.read().decode())
                ip = data.get("ip", "").strip()
                if ip and not _is_local_ip(ip):
                    return ip
        except Exception:
            pass
    except Exception:
        # Any other error, skip
        pass
    
    return None

