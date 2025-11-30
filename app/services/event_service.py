import logging
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit import AuditLog
from app.models.consent import EventNameEnum, PurposeEnum
from app.schemas.events import EventIn, EventResponse
from app.services.decision_service import decide
from app.services.provider_integrations import (
    send_to_google_ads_sync,
    send_to_google_analytics_sync,
)
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import get_utc_now

logger = logging.getLogger(__name__)

_EVENT_PURPOSE_MAP: Dict[EventNameEnum, PurposeEnum] = {
    EventNameEnum.PAGE_VIEW: PurposeEnum.ANALYTICS,
    EventNameEnum.PURCHASE: PurposeEnum.ANALYTICS,
    EventNameEnum.SIGNUP: PurposeEnum.ANALYTICS,
    EventNameEnum.AD_CLICK: PurposeEnum.ADS,
    EventNameEnum.NEWSLETTER_OPEN: PurposeEnum.EMAIL,
    EventNameEnum.LOCATION_PING: PurposeEnum.LOCATION,
}


def map_event_to_purpose(event_name: EventNameEnum) -> PurposeEnum:
    try:
        return _EVENT_PURPOSE_MAP[event_name]
    except KeyError as exc:  # pragma: no cover - defensive, schema guards earlier
        raise ValueError("unsupported_event") from exc


async def _forward_to_webhook(
    url: str, payload: Dict[str, Any], timeout: float = 5.0
) -> bool:
    """Forward event to external webhook URL."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        logger.warning(f"Failed to forward event to {url}: {e}")
        return False


def _forward_to_webhook_sync(
    url: str, payload: Dict[str, Any], timeout: float = 5.0
) -> bool:
    """Synchronous version for backward compatibility."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        logger.warning(f"Failed to forward event to {url}: {e}")
        return False


def handle_analytics_event(
    event_name: EventNameEnum, properties: Dict[str, Any], user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Handle analytics events with priority:
    1. Google Analytics (if configured)
    2. Webhook URL (if configured)
    3. Return payload for logging
    """
    payload = {"provider": "analytics", "event_name": event_name.value, "properties": properties}
    
    # Try Google Analytics first
    if settings.GA_MEASUREMENT_ID and settings.GA_API_SECRET:
        success = send_to_google_analytics_sync(event_name, properties, user_id)
        if success:
            return {"forwarded": True, "provider": "google_analytics", **payload}
    
    # Fallback to webhook
    if settings.ANALYTICS_WEBHOOK_URL:
        success = _forward_to_webhook_sync(settings.ANALYTICS_WEBHOOK_URL, payload)
        return {"forwarded": success, "provider": "webhook", **payload} if success else None
    
    return payload


def handle_ads_event(
    event_name: EventNameEnum, properties: Dict[str, Any], user_id: str
) -> Optional[Dict[str, Any]]:
    """
    Handle ads events with priority:
    1. Google Ads (if configured)
    2. Webhook URL (if configured)
    3. Return payload for logging
    """
    payload = {"provider": "ads", "event_name": event_name.value, "properties": properties}
    
    # Try Google Ads first
    if all([
        settings.GOOGLE_ADS_CUSTOMER_ID,
        settings.GOOGLE_ADS_DEVELOPER_TOKEN,
        settings.GOOGLE_ADS_CLIENT_ID,
        settings.GOOGLE_ADS_CLIENT_SECRET,
        settings.GOOGLE_ADS_REFRESH_TOKEN,
    ]):
        success = send_to_google_ads_sync(event_name, properties, user_id)
        if success:
            return {"forwarded": True, "provider": "google_ads", **payload}
    
    # Fallback to webhook
    if settings.ADS_WEBHOOK_URL:
        success = _forward_to_webhook_sync(settings.ADS_WEBHOOK_URL, payload)
        return {"forwarded": success, "provider": "webhook", **payload} if success else None
    
    return payload


def handle_email_event(
    event_name: EventNameEnum, properties: Dict[str, Any], user_id: str
) -> Optional[Dict[str, Any]]:
    payload = {"provider": "email", "event_name": event_name.value, "properties": properties}
    if settings.EMAIL_WEBHOOK_URL:
        success = _forward_to_webhook_sync(settings.EMAIL_WEBHOOK_URL, payload)
        return {"forwarded": success, **payload} if success else None
    return payload


def handle_location_event(
    event_name: EventNameEnum, properties: Dict[str, Any], user_id: str
) -> Optional[Dict[str, Any]]:
    payload = {"provider": "location", "event_name": event_name.value, "properties": properties}
    if settings.LOCATION_WEBHOOK_URL:
        success = _forward_to_webhook_sync(settings.LOCATION_WEBHOOK_URL, payload)
        return {"forwarded": success, **payload} if success else None
    return payload


def route_event_to_provider(
    purpose: PurposeEnum, event_name: EventNameEnum, properties: Dict[str, Any], user_id: str
) -> Optional[Dict[str, Any]]:
    if purpose == PurposeEnum.ANALYTICS:
        return handle_analytics_event(event_name, properties, user_id)
    if purpose == PurposeEnum.ADS:
        return handle_ads_event(event_name, properties, user_id)
    if purpose == PurposeEnum.EMAIL:
        return handle_email_event(event_name, properties, user_id)
    if purpose == PurposeEnum.LOCATION:
        return handle_location_event(event_name, properties, user_id)
    return None


def process_event(db: Session, event: EventIn, client_ip: str) -> EventResponse:
    purpose = map_event_to_purpose(event.event_name)
    fallback_region = detect_region_from_ip(client_ip)

    decision = decide(db, event.user_id, purpose, fallback_region=fallback_region)
    allowed = bool(decision["allowed"])
    reason = str(decision["reason"])
    policy_snapshot = decision.get("policy_snapshot")

    forwarded_result = None
    if allowed:
        forwarded_result = route_event_to_provider(
            purpose, event.event_name, event.properties, str(event.user_id)
        )

    # Build audit details
    audit_details = {
        "event_name": event.event_name.value,
        "purpose": purpose.value,
        "allowed": allowed,
        "reason": reason,
    }
    
    if forwarded_result:
        audit_details["forwarded"] = True
        audit_details["forwarded_result"] = forwarded_result
    else:
        audit_details["forwarded"] = False

    audit = AuditLog(
        user_id=event.user_id,
        action="event.processed",
        details=audit_details,
        created_at=get_utc_now(),
        policy_snapshot=policy_snapshot,
    )
    db.add(audit)
    db.commit()

    return EventResponse(accepted=allowed, reason=reason)

