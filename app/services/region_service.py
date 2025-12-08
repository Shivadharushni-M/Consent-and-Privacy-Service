from pathlib import Path
from typing import Optional

from app.config import settings
from app.models.consent import RegionEnum

try:
    from geoip2.database import Reader
except ImportError:
    Reader = None


GEOIP_DB_PATH = Path(__file__).resolve().parent.parent / "geoip" / "GeoLite2-Country.mmdb"
_MAXMIND_READY = bool(settings.MAXMIND_ACCOUNT_ID and settings.MAXMIND_LICENSE_KEY)
_GEOIP_READER: Optional["Reader"] = None

if _MAXMIND_READY and Reader is not None:
    try:
        if GEOIP_DB_PATH.exists():
            _GEOIP_READER = Reader(str(GEOIP_DB_PATH))
    except Exception:
        _GEOIP_READER = None


EU_COUNTRIES = frozenset({"AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "NO", "PL", "PT", "RO", "SE", "SI", "SK"})


def detect_region_from_ip(ip: Optional[str]) -> RegionEnum:
    normalized_ip = (ip or "").strip()
    if _is_local_ip(normalized_ip):
        public_ip = _get_public_ip()
        normalized_ip = public_ip if public_ip and not _is_local_ip(public_ip) else ""
    if not normalized_ip:
        return RegionEnum.ROW
    result = _detect_with_maxmind(normalized_ip)
    return result if result else RegionEnum.ROW


def _detect_with_maxmind(ip: str) -> Optional[RegionEnum]:
    if not ip or _GEOIP_READER is None:
        return None
    try:
        iso_code = (_GEOIP_READER.country(ip).country.iso_code or "").upper()
        return _map_iso_to_region(iso_code) if iso_code else None
    except Exception:
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
    if normalized_iso == "GB":
        return RegionEnum.UK
    try:
        return RegionEnum(normalized_iso)
    except ValueError:
        return RegionEnum.ROW


def _is_local_ip(ip: str) -> bool:
    if not ip:
        return True
    normalized = ip.lower()
    return normalized.startswith(("127.", "localhost", "192.168.", "10.", "172.16.")) or normalized == "::1"


def _get_public_ip() -> Optional[str]:
    services = [("https://api.ipify.org?format=json", "json"), ("https://api64.ipify.org?format=json", "json"), ("https://icanhazip.com", "text"), ("https://ifconfig.me/ip", "text"), ("https://checkip.amazonaws.com", "text")]
    try:
        import httpx
        for service_url, response_type in services:
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.get(service_url)
                    response.raise_for_status()
                    ip = (response.json().get("ip", "") if response_type == "json" else response.text).strip()
                    if ip and not _is_local_ip(ip):
                        return ip
            except Exception:
                continue
    except ImportError:
        try:
            import urllib.request, json
            with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as response:
                ip = json.loads(response.read().decode()).get("ip", "").strip()
                if ip and not _is_local_ip(ip):
                    return ip
        except Exception:
            pass
    except Exception:
        pass
    return None

