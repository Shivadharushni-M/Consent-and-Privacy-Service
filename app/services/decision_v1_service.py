from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog, EventTypeEnum
from app.models.catalog import Purpose, PurposeGroup, Vendor
from app.models.consent import ConsentHistory, PurposeEnum, RegionEnum, StatusEnum
from app.models.policy import Policy, PolicyVersion
from app.services import subject_service
from app.utils.helpers import get_utc_now, validate_region


def evaluate_decision(
    db: Session,
    *,
    subject_external_id: Optional[str] = None,
    subject_id: Optional[UUID] = None,
    purpose_code: str,
    vendor_code: Optional[str] = None,
    region_code: str,
    timestamp: datetime,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    # Resolve subject
    if subject_id:
        from app.services.user_service import get_user
        user = get_user(db, subject_id)
    elif subject_external_id:
        user = subject_service.get_subject_by_external_id(db, subject_external_id, tenant_id)
    else:
        return {
            "allowed": False,
            "decision": "no_subject",
            "legal_basis": None,
            "source": None,
            "policy_version_id": None,
            "consent_record_id": None,
            "reasoning": ["subject_not_provided"],
            "effective_at": timestamp,
        }
    
    purpose = PurposeEnum(purpose_code)
    region = validate_region(region_code)
    
    # Get applicable policy version
    policy_version = get_applicable_policy_version(db, region, timestamp, tenant_id)
    if not policy_version:
        return {
            "allowed": False,
            "decision": "no_policy",
            "legal_basis": None,
            "source": None,
            "policy_version_id": None,
            "consent_record_id": None,
            "reasoning": ["no_policy_version_found"],
            "effective_at": timestamp,
        }
    
    # Evaluate using policy matrix
    decision_result = evaluate_policy_matrix(
        db=db,
        user_id=user.id,
        purpose=purpose,
        vendor_code=vendor_code,
        policy_version=policy_version,
        region=region,
        timestamp=timestamp,
        tenant_id=tenant_id,
    )
    
    # Create audit log
    audit = AuditLog(
        tenant_id=tenant_id,
        subject_id=user.id,
        actor_type="system",
        event_type=EventTypeEnum.DECISION_EVALUATED.value,
        action="decision_evaluated",
        details={
            "user_id": str(user.id),
            "purpose": purpose_code,
            "vendor": vendor_code,
            "region": region_code,
            "allowed": decision_result["allowed"],
            "decision": decision_result["decision"],
        },
        policy_snapshot={"policy_version_id": str(policy_version.id)},
        event_time=timestamp,
    )
    db.add(audit)
    db.commit()
    
    # Build evidence object
    evidence = {
        "policy_version_id": str(policy_version.id),
        "consent_record_id": str(decision_result.get("consent_record_id")) if decision_result.get("consent_record_id") else None,
        "reasoning_steps": decision_result["reasoning"],
    }
    
    return {
        "allowed": decision_result["allowed"],
        "decision": decision_result["decision"],
        "legal_basis": decision_result.get("legal_basis"),
        "source": decision_result.get("source"),
        "policy_version_id": policy_version.id,
        "consent_record_id": decision_result.get("consent_record_id"),
        "reasoning": decision_result["reasoning"],
        "evidence": evidence,
        "effective_at": timestamp,
    }


def get_applicable_policy_version(
    db: Session,
    region: RegionEnum,
    timestamp: datetime,
    tenant_id: Optional[str] = None,
) -> Optional[PolicyVersion]:
    query = db.query(PolicyVersion).join(Policy).filter(
        Policy.region_code == region.value,
        PolicyVersion.effective_from <= timestamp,
        (PolicyVersion.effective_to.is_(None) | (PolicyVersion.effective_to > timestamp))
    )
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    return query.order_by(PolicyVersion.effective_from.desc()).first()


def evaluate_policy_matrix(
    db: Session,
    user_id: UUID,
    purpose: PurposeEnum,
    vendor_code: Optional[str],
    policy_version: PolicyVersion,
    region: RegionEnum,
    timestamp: datetime,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    matrix = policy_version.matrix
    reasoning = []
    
    # Get default decision
    default_decision = matrix.get("default_decision", "deny")
    rules = matrix.get("rules", [])
    
    # Resolve vendor_id if vendor_code provided
    vendor_id = None
    if vendor_code:
        vendor = db.query(Vendor).filter(
            Vendor.code == vendor_code,
            (Vendor.tenant_id == tenant_id) if tenant_id else True
        ).first()
        if vendor:
            vendor_id = vendor.id
            reasoning.append(f"vendor_resolved:{vendor_code}")
        else:
            reasoning.append(f"vendor_not_found:{vendor_code}")
    
    # Get purpose and purpose group info for precedence evaluation
    purpose_obj = db.query(Purpose).filter(
        Purpose.code == purpose.value,
        (Purpose.tenant_id == tenant_id) if tenant_id else True
    ).first()
    
    purpose_group_id = None
    purpose_group_code = None
    purpose_group_precedence = None
    if purpose_obj and purpose_obj.purpose_group_id:
        purpose_group = db.query(PurposeGroup).filter(
            PurposeGroup.id == purpose_obj.purpose_group_id
        ).first()
        if purpose_group:
            purpose_group_id = purpose_group.id
            purpose_group_code = purpose_group.code
            purpose_group_precedence = purpose_group.precedence
            reasoning.append(f"purpose_group_found:{purpose_group.code}:precedence:{purpose_group.precedence}")
    
    # Find applicable rule with precedence: vendor > purpose > purpose_group > default
    applicable_rule = None
    rule_precedence = -1  # Lower number = higher precedence
    
    for rule in rules:
        rule_purpose = rule.get("purpose")
        rule_vendor = rule.get("vendor")
        rule_purpose_group = rule.get("purpose_group")
        
        # Check if rule matches
        matches = False
        current_precedence = 3  # Default (lowest precedence)
        
        # Vendor-specific rule (highest precedence = 0)
        if vendor_code and rule_vendor == vendor_code and rule_purpose == purpose.value:
            matches = True
            current_precedence = 0
        # Purpose-specific rule (precedence = 1)
        elif not vendor_code and rule_vendor is None and rule_purpose == purpose.value and rule_purpose_group is None:
            matches = True
            current_precedence = 1
        # Purpose group rule (precedence = 2)
        elif rule_purpose_group and purpose_group_code:
            # Check if purpose belongs to this group
            if rule_purpose_group == purpose_group_code:
                matches = True
                current_precedence = 2
        
        if matches and (current_precedence < rule_precedence or rule_precedence == -1):
            applicable_rule = rule
            rule_precedence = current_precedence
    
    if not applicable_rule:
        reasoning.append(f"no_rule_for_purpose_{purpose.value}")
        return {
            "allowed": default_decision == "allow",
            "decision": default_decision,
            "source": "policy_default",
            "reasoning": reasoning,
        }
    
    required_legal_basis = applicable_rule.get("required_legal_basis")
    allowed_without_consent = applicable_rule.get("allowed_without_consent", False)
    reasoning.append(f"rule_applied:precedence_{rule_precedence}")
    
    # Check for consent with precedence: vendor-specific > purpose-level > purpose-group
    # First check vendor-specific consent
    consent = None
    if vendor_id:
        consent_query = db.query(ConsentHistory).filter(
            ConsentHistory.user_id == user_id,
            ConsentHistory.purpose == purpose,
            ConsentHistory.vendor_id == vendor_id,
            ConsentHistory.valid_from <= timestamp,
            (ConsentHistory.valid_until.is_(None) | (ConsentHistory.valid_until > timestamp)),
            ConsentHistory.status.in_([StatusEnum.GRANTED]),
        )
        consent = consent_query.order_by(ConsentHistory.timestamp.desc()).first()
        if consent:
            reasoning.append("vendor_specific_consent_found")
    
    # If no vendor-specific consent, check purpose-level consent
    if not consent:
        consent_query = db.query(ConsentHistory).filter(
            ConsentHistory.user_id == user_id,
            ConsentHistory.purpose == purpose,
            ConsentHistory.vendor_id.is_(None),  # Purpose-level consents have no vendor_id
            ConsentHistory.valid_from <= timestamp,
            (ConsentHistory.valid_until.is_(None) | (ConsentHistory.valid_until > timestamp)),
            ConsentHistory.status.in_([StatusEnum.GRANTED]),
        )
        consent = consent_query.order_by(ConsentHistory.timestamp.desc()).first()
        if consent:
            reasoning.append("purpose_level_consent_found")
    
    # If still no consent and purpose has a group, could check group-level (but spec doesn't specify group consents)
    # So we stop at purpose-level
    
    if consent:
        reasoning.append("consent_found")
        return {
            "allowed": True,
            "decision": "allow",
            "legal_basis": consent.legal_basis or "consent",
            "source": "consent",
            "consent_record_id": consent.id,
            "reasoning": reasoning,
        }
    
    if allowed_without_consent:
        reasoning.append("allowed_without_consent_per_policy")
        return {
            "allowed": True,
            "decision": "allow",
            "legal_basis": required_legal_basis or "legitimate_interest",
            "source": "policy_default",
            "reasoning": reasoning,
        }
    
    reasoning.append("consent_required_but_not_found")
    return {
        "allowed": False,
        "decision": "deny",
        "legal_basis": None,
        "source": "policy_requires_consent",
        "reasoning": reasoning,
    }
