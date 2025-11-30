import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import (
    PurposeEnum,
    RegionEnum,
    StatusEnum,
    VendorConsent,
    VendorEnum,
)
from app.services import user_service
from app.utils.helpers import build_policy_snapshot, get_utc_now, validate_region


def grant_vendor_consent(
    db: Session,
    user_id: uuid.UUID,
    vendor: VendorEnum,
    purpose: PurposeEnum,
    region: RegionEnum,
    expires_at: Optional[datetime] = None,
) -> VendorConsent:
    user = user_service.get_user(db, user_id)
    region_value = validate_region(region)
    snapshot = build_policy_snapshot(region_value)

    vendor_consent = VendorConsent(
        user_id=user.id,
        vendor=vendor,
        purpose=purpose,
        status=StatusEnum.GRANTED,
        region=region_value,
        expires_at=expires_at,
        policy_snapshot=snapshot,
    )
    audit = AuditLog(
        user_id=user.id,
        action="VENDOR_CONSENT_GRANTED",
        details={
            "vendor": vendor.value,
            "purpose": purpose.value,
            "region": region_value.value,
        },
        policy_snapshot=snapshot,
    )
    db.add_all([vendor_consent, audit])
    db.commit()
    db.refresh(vendor_consent)
    return vendor_consent


def revoke_vendor_consent(
    db: Session,
    user_id: uuid.UUID,
    vendor: VendorEnum,
    purpose: PurposeEnum,
    region: RegionEnum,
    expires_at: Optional[datetime] = None,
) -> VendorConsent:
    user = user_service.get_user(db, user_id)
    region_value = validate_region(region)
    snapshot = build_policy_snapshot(region_value)

    vendor_consent = VendorConsent(
        user_id=user.id,
        vendor=vendor,
        purpose=purpose,
        status=StatusEnum.REVOKED,
        region=region_value,
        expires_at=expires_at,
        policy_snapshot=snapshot,
    )
    audit = AuditLog(
        user_id=user.id,
        action="VENDOR_CONSENT_REVOKED",
        details={
            "vendor": vendor.value,
            "purpose": purpose.value,
            "region": region_value.value,
        },
        policy_snapshot=snapshot,
    )
    db.add_all([vendor_consent, audit])
    db.commit()
    db.refresh(vendor_consent)
    return vendor_consent


def get_vendor_consent_status(
    db: Session, user_id: uuid.UUID, vendor: VendorEnum, purpose: PurposeEnum
) -> Optional[StatusEnum]:
    """Get the latest vendor consent status for a user, vendor, and purpose."""
    now = get_utc_now()
    latest = (
        db.query(VendorConsent)
        .filter(
            VendorConsent.user_id == user_id,
            VendorConsent.vendor == vendor,
            VendorConsent.purpose == purpose,
        )
        .order_by(VendorConsent.timestamp.desc())
        .first()
    )

    if not latest:
        return None

    # Check if expired
    if latest.expires_at and latest.expires_at < now:
        return StatusEnum.REVOKED

    return latest.status


def get_vendor_consents_for_purpose(
    db: Session, user_id: uuid.UUID, purpose: PurposeEnum
) -> Dict[VendorEnum, StatusEnum]:
    """Get all vendor consent statuses for a given purpose."""
    now = get_utc_now()
    consents = (
        db.query(VendorConsent)
        .filter(
            VendorConsent.user_id == user_id,
            VendorConsent.purpose == purpose,
        )
        .order_by(VendorConsent.timestamp.desc())
        .all()
    )

    result: Dict[VendorEnum, StatusEnum] = {}
    seen_vendors = set()

    for consent in consents:
        if consent.vendor in seen_vendors:
            continue

        # Check if expired
        if consent.expires_at and consent.expires_at < now:
            result[consent.vendor] = StatusEnum.REVOKED
        else:
            result[consent.vendor] = consent.status
        seen_vendors.add(consent.vendor)

    return result


def get_vendor_history(
    db: Session, user_id: uuid.UUID, vendor: Optional[VendorEnum] = None
) -> List[VendorConsent]:
    """Get vendor consent history for a user, optionally filtered by vendor."""
    query = db.query(VendorConsent).filter(VendorConsent.user_id == user_id)
    if vendor:
        query = query.filter(VendorConsent.vendor == vendor)
    return query.order_by(VendorConsent.timestamp.desc()).all()

