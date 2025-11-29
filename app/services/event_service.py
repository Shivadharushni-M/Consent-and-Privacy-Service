from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import EventNameEnum, PurposeEnum
from app.schemas.events import EventIn, EventResponse
from app.services.decision_service import decide
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import get_utc_now

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


def handle_analytics_event(event_name: EventNameEnum, properties: Dict[str, Any]) -> Dict[str, Any]:
    return {"provider": "analytics", "event_name": event_name.value, "properties": properties}


def handle_ads_event(event_name: EventNameEnum, properties: Dict[str, Any]) -> Dict[str, Any]:
    return {"provider": "ads", "event_name": event_name.value, "properties": properties}


def handle_email_event(event_name: EventNameEnum, properties: Dict[str, Any]) -> Dict[str, Any]:
    return {"provider": "email", "event_name": event_name.value, "properties": properties}


def handle_location_event(event_name: EventNameEnum, properties: Dict[str, Any]) -> Dict[str, Any]:
    return {"provider": "location", "event_name": event_name.value, "properties": properties}


def route_event_to_provider(
    purpose: PurposeEnum, event_name: EventNameEnum, properties: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    if purpose == PurposeEnum.ANALYTICS:
        return handle_analytics_event(event_name, properties)
    if purpose == PurposeEnum.ADS:
        return handle_ads_event(event_name, properties)
    if purpose == PurposeEnum.EMAIL:
        return handle_email_event(event_name, properties)
    if purpose == PurposeEnum.LOCATION:
        return handle_location_event(event_name, properties)
    return None


def process_event(db: Session, event: EventIn, client_ip: str) -> EventResponse:
    purpose = map_event_to_purpose(event.event_name)
    fallback_region = detect_region_from_ip(client_ip)

    decision = decide(db, event.user_id, purpose, fallback_region=fallback_region)
    allowed = bool(decision["allowed"])
    reason = str(decision["reason"])

    if allowed:
        route_event_to_provider(purpose, event.event_name, event.properties)

    audit = AuditLog(
        user_id=event.user_id,
        action="event.processed",
        details={
            "event_name": event.event_name.value,
            "purpose": purpose.value,
            "allowed": allowed,
            "reason": reason,
        },
        created_at=get_utc_now(),
    )
    db.add(audit)
    db.commit()

    return EventResponse(accepted=allowed, reason=reason)

