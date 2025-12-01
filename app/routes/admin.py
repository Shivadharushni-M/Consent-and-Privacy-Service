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
    """List Users"""
    try:
        query = db.query(User)
        if region:
            query = query.filter(User.region == region)
        return query.order_by(User.created_at.desc()).all()
    except Exception as e:
        import traceback
        print(f"Error in list_users: {e}")
        print(traceback.format_exc())
        return []


@router.get("/consents/{user_id}", response_model=List[ConsentResponse])
def list_user_consents(user_id: UUID, db: Session = Depends(get_db)):
    """List User Consents"""
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


@router.get("/audit", response_model=List[AuditLogResponse], summary="List Audit Logs", description="Retrieve audit logs with optional filtering by action, purpose, and region")
def list_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID (UUID)"),
    action: Optional[str] = Query(default=None, description="Filter by action type"),
    purpose: Optional[PurposeEnum] = Query(default=None, description="Filter by purpose"),
    region: Optional[RegionEnum] = Query(default=None, description="Filter by region"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
):
    """List Audit Logs - Get all audit logs with optional filtering"""
    try:
        import uuid
        
        # Check if table exists by attempting a simple query
        try:
            query = db.query(AuditLog)
        except Exception as table_error:
            # If table doesn't exist, return empty result
            return []
        
        # Filter by user_id if provided
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                query = query.filter(AuditLog.user_id == user_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")
        
        # Filter by action if provided
        if action:
            query = query.filter(AuditLog.action == action)
        
        # Filter by purpose if provided (from details JSONB)
        if purpose:
            query = query.filter(cast(AuditLog.details["purpose"], String) == purpose.value)
        
        # Filter by region if provided (from details JSONB)
        if region:
            query = query.filter(cast(AuditLog.details["region"], String) == region.value)
        
        # Order by created_at descending (most recent first)
        query = query.order_by(desc(AuditLog.created_at))
        
        # Apply pagination
        try:
            logs = query.offset(offset).limit(limit).all()
            # Handle None details by converting to empty dict
            for log in logs:
                if log.details is None:
                    log.details = {}
            return logs
        except Exception as query_error:
            # If query fails, return empty result with error message
            import traceback
            error_details = traceback.format_exc()
            print(f"Query error in list_audit_logs: {query_error}")
            print(error_details)
            return []
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
    """List Subject Requests"""
    try:
        return (
            db.query(SubjectRequest)
            .order_by(SubjectRequest.requested_at.desc())
            .all()
        )
    except Exception as e:
        import traceback
        print(f"Error in list_subject_requests: {e}")
        print(traceback.format_exc())
        return []
