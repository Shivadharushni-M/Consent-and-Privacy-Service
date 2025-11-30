from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, String
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import PurposeEnum, RegionEnum, RequestTypeEnum, SubjectRequest
from app.models.policy import Policy, PolicyVersion
from app.schemas.consent import AuditLogResponse
from app.schemas.policy import PolicyVersionResponse
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-v1"],
    dependencies=[Depends(api_key_auth)],
)


@router.get("/audits", response_model=List[AuditLogResponse])
def list_audit_logs(
    subject_id: Optional[UUID] = Query(None, description="Filter by subject ID"),
    subject_external_id: Optional[str] = Query(None, description="Filter by subject external ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    from_time: Optional[datetime] = Query(None, alias="from", description="Filter from timestamp"),
    to_time: Optional[datetime] = Query(None, alias="to", description="Filter to timestamp"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    db: Session = Depends(get_db),
):
    """
    Query audit logs with filters.
    Supports filtering by subject, event type, time range, and tenant.
    """
    query = db.query(AuditLog)
    
    if subject_id:
        query = query.filter(
            (AuditLog.subject_id == subject_id) | (AuditLog.user_id == subject_id)
        )
    elif subject_external_id:
        # Would need to resolve external_id to subject_id
        from app.services import subject_service
        try:
            user = subject_service.get_subject_by_external_id(db, subject_external_id, tenant_id)
            query = query.filter(
                (AuditLog.subject_id == user.id) | (AuditLog.user_id == user.id)
            )
        except ValueError:
            # Subject not found, return empty result
            return []
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if from_time:
        query = query.filter(AuditLog.event_time >= from_time)
    
    if to_time:
        query = query.filter(AuditLog.event_time <= to_time)
    
    if tenant_id:
        query = query.filter(AuditLog.tenant_id == tenant_id)
    
    return query.order_by(AuditLog.event_time.desc()).all()


@router.get("/exports/{request_id}", response_model=Dict[str, Any])
def get_export_details(request_id: UUID, db: Session = Depends(get_db)):
    """Admin view of export request details."""
    request = db.get(SubjectRequest, request_id)
    if not request or request.request_type != RequestTypeEnum.EXPORT:
        raise HTTPException(status_code=404, detail="Export request not found")
    
    return {
        "id": str(request.id),
        "type": request.request_type.value,
        "status": request.status.value,
        "result_location": request.result_location,
        "error_message": request.error_message,
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        "completed_at": request.completed_at.isoformat() if request.completed_at else None,
    }


@router.get("/deletions/{request_id}", response_model=Dict[str, Any])
def get_deletion_details(request_id: UUID, db: Session = Depends(get_db)):
    """Admin view of deletion request details."""
    request = db.get(SubjectRequest, request_id)
    if not request or request.request_type != RequestTypeEnum.DELETE:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    
    return {
        "id": str(request.id),
        "type": request.request_type.value,
        "status": request.status.value,
        "error_message": request.error_message,
        "requested_at": request.requested_at.isoformat() if request.requested_at else None,
        "completed_at": request.completed_at.isoformat() if request.completed_at else None,
    }


@router.get("/policy-snapshots", response_model=List[PolicyVersionResponse])
def get_policy_snapshots(
    region_code: Optional[str] = Query(None, description="Filter by region code"),
    timestamp: Optional[datetime] = Query(None, description="Get policy version effective at this timestamp"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    db: Session = Depends(get_db),
):
    """
    Query policy snapshots by region and timestamp.
    Returns the policy version effective at that time.
    """
    query = db.query(PolicyVersion).join(Policy)
    
    if region_code:
        query = query.filter(Policy.region_code == region_code)
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    if timestamp:
        query = query.filter(
            PolicyVersion.effective_from <= timestamp,
            (PolicyVersion.effective_to.is_(None) | (PolicyVersion.effective_to > timestamp))
        )
    
    return query.all()
