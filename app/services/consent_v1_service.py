from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, EventTypeEnum
from app.models.catalog import Vendor
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum
from app.models.policy import PolicyVersion
from app.services import subject_service
from app.services.consent_service import grant_consent, revoke_consent
from app.utils.helpers import build_policy_snapshot, get_utc_now, validate_region


def create_consent_record(
    db: Session,
    *,
    subject_external_id: Optional[str] = None,
    subject_id: Optional[UUID] = None,
    purpose_code: str,
    vendor_code: Optional[str] = None,
    legal_basis: Optional[str] = None,  # Should be LegalBasisEnum but keeping as string for flexibility
    status: str,
    region_code: str,
    valid_from: Optional[datetime] = None,
    valid_until: Optional[datetime] = None,
    policy_version_id: Optional[UUID] = None,
    source: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[str] = None,
) -> ConsentHistory:
    # Resolve subject
    if subject_id:
        from app.services.user_service import get_user
        user = get_user(db, subject_id)
    elif subject_external_id:
        user = subject_service.get_subject_by_external_id(db, subject_external_id, tenant_id)
    else:
        raise ValueError("subject_id or subject_external_id required")
    
    purpose = PurposeEnum(purpose_code)
    region = validate_region(region_code)
    status_enum = StatusEnum(status.lower())
    
    # Get policy version if not provided
    if not policy_version_id:
        policy_version = get_current_policy_version(db, region, tenant_id)
        if policy_version:
            policy_version_id = policy_version.id
    
    valid_from_dt = valid_from or get_utc_now()
    granted_at = valid_from_dt if status_enum == StatusEnum.GRANTED else None
    
    # Resolve vendor_id from vendor_code if provided
    vendor_id = None
    if vendor_code:
        vendor = db.query(Vendor).filter(
            Vendor.code == vendor_code,
            (Vendor.tenant_id == tenant_id) if tenant_id else True
        ).first()
        if vendor:
            vendor_id = vendor.id
    
    # Check for overlapping active consents and update them
    # Spec: "If existing active consent for same (subject, purpose, vendor, legal_basis) overlaps time window, 
    # update status and set end date of previous if needed."
    now = get_utc_now()
    # Build overlap query: consents that overlap with the new consent's time window
    overlap_query = db.query(ConsentHistory).filter(
        ConsentHistory.user_id == user.id,
        ConsentHistory.purpose == purpose,
        ConsentHistory.vendor_id == vendor_id,
        ConsentHistory.legal_basis == legal_basis,
        ConsentHistory.status == StatusEnum.GRANTED,
    )
    # Overlap condition: existing consent starts before new consent ends AND
    # existing consent ends after new consent starts (or has no end)
    if valid_until:
        overlap_query = overlap_query.filter(
            ConsentHistory.valid_from <= valid_until,
            (ConsentHistory.valid_until.is_(None) | (ConsentHistory.valid_until >= valid_from_dt)),
        )
    else:
        # New consent has no end date, so any existing consent that hasn't ended overlaps
        overlap_query = overlap_query.filter(
            (ConsentHistory.valid_until.is_(None) | (ConsentHistory.valid_until >= valid_from_dt)),
        )
    overlapping_consents = overlap_query.all()
    
    old_consent_data = None
    for existing_consent in overlapping_consents:
        # Store old data for audit log
        if not old_consent_data:
            old_consent_data = {
                "id": str(existing_consent.id),
                "status": existing_consent.status.value,
                "valid_from": existing_consent.valid_from.isoformat() if existing_consent.valid_from else None,
                "valid_until": existing_consent.valid_until.isoformat() if existing_consent.valid_until else None,
            }
        
        # Set end date of previous consent to just before new consent starts
        if existing_consent.valid_from < valid_from_dt:
            existing_consent.valid_until = valid_from_dt
            existing_consent.expires_at = valid_from_dt
        else:
            # If new consent starts before existing, mark existing as withdrawn
            existing_consent.status = StatusEnum.WITHDRAWN
            existing_consent.valid_until = valid_from_dt
            existing_consent.expires_at = valid_from_dt
    
    consent = ConsentHistory(
        tenant_id=tenant_id,
        user_id=user.id,
        purpose=purpose,
        vendor_id=vendor_id,
        legal_basis=legal_basis,
        status=status_enum,
        region=region,
        granted_at=granted_at,
        valid_from=valid_from_dt,
        valid_until=valid_until,
        timestamp=get_utc_now(),
        expires_at=valid_until,
        policy_version_id=policy_version_id,
        policy_snapshot=build_policy_snapshot(region),
        source=source,
        user_agent=user_agent,
        ip_address=ip_address,
        meta=meta,
    )
    
    # Build audit log with old vs new data
    audit_details = {
        "purpose": purpose_code,
        "vendor": vendor_code,
        "legal_basis": legal_basis,
        "status": status,
        "new": {
            "status": status,
            "valid_from": valid_from_dt.isoformat(),
            "valid_until": valid_until.isoformat() if valid_until else None,
        }
    }
    if old_consent_data:
        audit_details["old"] = old_consent_data
    
    audit = AuditLog(
        tenant_id=tenant_id,
        subject_id=user.id,
        actor_type="subject",
        event_type=EventTypeEnum.CONSENT_GRANTED.value if status_enum == StatusEnum.GRANTED else EventTypeEnum.CONSENT_DENIED.value,
        action="CONSENT_GRANTED" if status_enum == StatusEnum.GRANTED else "CONSENT_DENIED",
        details=audit_details,
        policy_snapshot=consent.policy_snapshot,
        event_time=get_utc_now(),
    )
    
    db.add_all([consent, audit])
    db.commit()
    db.refresh(consent)
    return consent


def get_current_policy_version(db: Session, region: RegionEnum, tenant_id: Optional[str] = None) -> Optional[PolicyVersion]:
    from app.models.policy import Policy
    now = get_utc_now()
    query = db.query(PolicyVersion).join(Policy).filter(
        Policy.region_code == region.value,
        PolicyVersion.effective_from <= now,
        (PolicyVersion.effective_to.is_(None) | (PolicyVersion.effective_to > now))
    )
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    return query.order_by(PolicyVersion.effective_from.desc()).first()


def query_consents(
    db: Session,
    *,
    subject_id: Optional[UUID] = None,
    subject_external_id: Optional[str] = None,
    purpose_code: Optional[str] = None,
    vendor_code: Optional[str] = None,
    status: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> List[ConsentHistory]:
    query = db.query(ConsentHistory)
    
    if subject_id:
        query = query.filter(ConsentHistory.user_id == subject_id)
    elif subject_external_id:
        user = subject_service.get_subject_by_external_id(db, subject_external_id, tenant_id)
        query = query.filter(ConsentHistory.user_id == user.id)
    
    if purpose_code:
        query = query.filter(ConsentHistory.purpose == PurposeEnum(purpose_code))
    
    if status:
        query = query.filter(ConsentHistory.status == StatusEnum(status.lower()))
    
    if tenant_id:
        # Match exact tenant_id (strict filtering for multi-tenant isolation)
        query = query.filter(ConsentHistory.tenant_id == tenant_id)
    
    return query.order_by(ConsentHistory.timestamp.desc()).all()


def revoke_consent_record(
    db: Session,
    *,
    subject_external_id: Optional[str] = None,
    subject_id: Optional[UUID] = None,
    purpose_code: str,
    vendor_code: Optional[str] = None,
    reason: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> ConsentHistory:
    # Resolve subject
    if subject_id:
        from app.services.user_service import get_user
        user = get_user(db, subject_id)
    elif subject_external_id:
        user = subject_service.get_subject_by_external_id(db, subject_external_id, tenant_id)
    else:
        raise ValueError("subject_id or subject_external_id required")
    
    purpose = PurposeEnum(purpose_code)
    now = get_utc_now()
    
    # Resolve vendor_id if vendor_code provided
    vendor_id = None
    if vendor_code:
        vendor = db.query(Vendor).filter(
            Vendor.code == vendor_code,
            (Vendor.tenant_id == tenant_id) if tenant_id else True
        ).first()
        if vendor:
            vendor_id = vendor.id
    
    # Find active consent (matching vendor if provided)
    query = db.query(ConsentHistory).filter(
        ConsentHistory.user_id == user.id,
        ConsentHistory.purpose == purpose,
        ConsentHistory.status == StatusEnum.GRANTED,
        (ConsentHistory.valid_until.is_(None) | (ConsentHistory.valid_until > now)),
    )
    if vendor_id is not None:
        query = query.filter(ConsentHistory.vendor_id == vendor_id)
    else:
        query = query.filter(ConsentHistory.vendor_id.is_(None))
    
    consent = query.order_by(ConsentHistory.timestamp.desc()).first()
    
    if not consent:
        raise ValueError("no_active_consent")
    
    # Store old consent data for audit log
    old_consent_data = {
        "id": str(consent.id),
        "status": consent.status.value,
        "valid_from": consent.valid_from.isoformat() if consent.valid_from else None,
        "valid_until": consent.valid_until.isoformat() if consent.valid_until else None,
    }
    
    # Create withdrawal record (use WITHDRAWN status per spec)
    withdrawal = ConsentHistory(
        tenant_id=tenant_id or consent.tenant_id,
        user_id=user.id,
        purpose=purpose,
        vendor_id=consent.vendor_id,
        legal_basis=consent.legal_basis,
        status=StatusEnum.WITHDRAWN,
        region=consent.region,
        granted_at=consent.granted_at,
        valid_from=consent.valid_from,
        valid_until=now,
        timestamp=now,
        expires_at=now,
        policy_version_id=consent.policy_version_id,
        policy_snapshot=consent.policy_snapshot,
        source=consent.source,
        meta={"withdrawal_reason": reason} if reason else None,
    )
    
    audit = AuditLog(
        tenant_id=tenant_id or consent.tenant_id,
        subject_id=user.id,
        actor_type="subject",
        event_type=EventTypeEnum.CONSENT_WITHDRAWN.value,
        action="CONSENT_REVOKED",
        details={
            "purpose": purpose_code,
            "vendor": vendor_code,
            "reason": reason,
            "old": old_consent_data,
            "new": {
                "status": StatusEnum.WITHDRAWN.value,
                "valid_until": now.isoformat(),
            }
        },
        policy_snapshot=withdrawal.policy_snapshot,
        event_time=now,
    )
    
    db.add_all([withdrawal, audit])
    db.commit()
    db.refresh(withdrawal)
    return withdrawal
