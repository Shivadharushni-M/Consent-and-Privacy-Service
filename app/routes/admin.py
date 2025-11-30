from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, String, desc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import (
    ConsentHistory,
    PurposeEnum,
    RegionEnum,
    SubjectRequest,
    User,
)
from app.schemas.consent import AuditLogResponse, ConsentResponse, SubjectRequestResponse
from app.schemas.user import UserResponse
from app.services import user_service
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(api_key_auth)],
)


@router.get("/users", response_model=List[UserResponse])
def list_users(
    region: Optional[RegionEnum] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if region:
        query = query.filter(User.region == region)
    return query.order_by(User.created_at.desc()).all()


@router.get("/consents/{user_id}", response_model=List[ConsentResponse])
def list_user_consents(user_id: UUID, db: Session = Depends(get_db)):
    try:
        user_service.get_user(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="user_not_found") from exc

    return (
        db.query(ConsentHistory)
        .filter(ConsentHistory.user_id == user_id)
        .order_by(ConsentHistory.timestamp.desc())
        .all()
    )


@router.get("/audit", response_model=List[AuditLogResponse], summary="List Audit Logs", description="Retrieve audit logs with optional filtering")
def list_audit_logs(
    action: Optional[str] = Query(default=None),
    purpose: Optional[PurposeEnum] = Query(default=None),
    region: Optional[RegionEnum] = Query(default=None),
    user_id: Optional[str] = Query(None, description="Filter by user ID (UUID)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
):
    """List Audit Logs - Get all audit logs with optional filtering"""
    try:
        import uuid
        
        query = db.query(AuditLog)
        
        # Filter by user_id if provided (backward compatibility)
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                query = query.filter(AuditLog.user_id == user_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")
        
        if action:
            query = query.filter(AuditLog.action == action)
        if purpose:
            query = query.filter(cast(AuditLog.details["purpose"], String) == purpose.value)
        if region:
            query = query.filter(cast(AuditLog.details["region"], String) == region.value)
        
        # Apply pagination
        total = query.count()
        logs = query.order_by(desc(AuditLog.created_at) if hasattr(AuditLog, 'created_at') else desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
        
        return logs
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in list_audit_logs: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}. Check server logs for details.")


@router.get("/subject-requests", response_model=List[SubjectRequestResponse])
def list_subject_requests(db: Session = Depends(get_db)):
    return (
        db.query(SubjectRequest)
        .order_by(SubjectRequest.requested_at.desc())
        .all()
    )
