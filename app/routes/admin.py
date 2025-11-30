from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List
from datetime import datetime
from app.db.database import get_db
from app.utils.security import api_key_auth
from app.models.audit import AuditLog

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(api_key_auth)])

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List Users"""
    return {"users": []}

@router.get("/consents/{user_id}")
def list_user_consents(user_id: str, db: Session = Depends(get_db)):
    """List User Consents"""
    return {"user_id": user_id, "consents": []}

@router.get("/audit", summary="List Audit Logs", description="Retrieve audit logs with optional filtering by user_id, action, and date range")
def list_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID (UUID)"),
    action: Optional[str] = Query(None, description="Filter by action type (e.g., 'grant', 'revoke')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db)
):
    """List Audit Logs - Get all audit logs with optional filtering"""
    try:
        import uuid
        
        # Check if table exists by attempting a simple query
        try:
            query = db.query(AuditLog)
        except Exception as table_error:
            # If table doesn't exist, return empty result
            return {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "logs": [],
                "message": "Audit logs table not found or not accessible"
            }
        
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
        
        # Order by timestamp descending (most recent first)
        query = query.order_by(desc(AuditLog.timestamp))
        
        # Apply pagination
        try:
            total = query.count()
            logs = query.offset(offset).limit(limit).all()
        except Exception as query_error:
            # If query fails, return empty result with error message
            import traceback
            error_details = traceback.format_exc()
            print(f"Query error in list_audit_logs: {query_error}")
            print(error_details)
            return {
                "total": 0,
                "limit": limit,
                "offset": offset,
                "logs": [],
                "error": str(query_error)
            }
        
        # Filter out None values and safely convert logs
        log_list = []
        for log in logs:
            if log is None:
                continue
            try:
                log_list.append({
                    "id": log.id,
                    "user_id": str(log.user_id) if log.user_id else None,
                    "action": log.action if log.action else None,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                })
            except AttributeError as attr_error:
                print(f"Error processing log entry: {attr_error}, log object: {log}")
                continue
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "logs": log_list
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in list_audit_logs: {e}")
        print(error_details)
        # Return error details in response for debugging
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}. Check server logs for details.")

@router.get("/subject-requests")
def list_subject_requests(db: Session = Depends(get_db)):
    """List Subject Requests"""
    return {"requests": []}
