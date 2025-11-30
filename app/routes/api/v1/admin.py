from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from app.db.database import get_db
from app.utils.security import api_key_auth

# Policies router
policies_router = APIRouter(prefix="/api/v1/admin/policies", tags=["admin-policies"], dependencies=[Depends(api_key_auth)])

@policies_router.post("", status_code=201)
def create_policy(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Policy"""
    return {"message": "Policy created", "data": request}

@policies_router.get("")
def list_policies(
    tenant_id: Optional[str] = Query(None, description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """List Policies"""
    return {"policies": [], "tenant_id": tenant_id}

@policies_router.post("/{policy_id}/versions", status_code=201)
def create_policy_version(policy_id: str, request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Policy Version"""
    return {"policy_id": policy_id, "message": "Policy version created", "data": request}

@policies_router.get("/{policy_id}/versions")
def list_policy_versions(policy_id: str, db: Session = Depends(get_db)):
    """List Policy Versions"""
    return {"policy_id": policy_id, "versions": []}

@policies_router.get("/{policy_id}/versions/{version_id}")
def get_policy_version(policy_id: str, version_id: str, db: Session = Depends(get_db)):
    """Get Policy Version"""
    return {"policy_id": policy_id, "version_id": version_id, "version": {}}

@policies_router.get("/snapshots")
def get_policy_snapshots(
    region_code: Optional[str] = Query(None, description="Region code"),
    db: Session = Depends(get_db)
):
    """Get Policy Snapshots"""
    return {"snapshots": [], "region_code": region_code}

# Catalog router
catalog_router = APIRouter(prefix="/api/v1/admin", tags=["admin-catalog"], dependencies=[Depends(api_key_auth)])

@catalog_router.post("/purposes", status_code=201)
def create_purpose(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Purpose"""
    return {"message": "Purpose created", "data": request}

@catalog_router.get("/purposes")
def list_purposes(db: Session = Depends(get_db)):
    """List Purposes"""
    return {"purposes": []}

@catalog_router.patch("/purposes/{purpose_id}")
def update_purpose(purpose_id: str, request: Dict[str, Any], db: Session = Depends(get_db)):
    """Update Purpose"""
    return {"purpose_id": purpose_id, "message": "Purpose updated", "data": request}

@catalog_router.post("/purpose-groups", status_code=201)
def create_purpose_group(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Purpose Group"""
    return {"message": "Purpose group created", "data": request}

@catalog_router.get("/purpose-groups")
def list_purpose_groups(db: Session = Depends(get_db)):
    """List Purpose Groups"""
    return {"purpose_groups": []}

@catalog_router.post("/vendors", status_code=201)
def create_vendor(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Vendor"""
    return {"message": "Vendor created", "data": request}

@catalog_router.get("/vendors")
def list_vendors(db: Session = Depends(get_db)):
    """List Vendors"""
    return {"vendors": []}

# Admin v1 router
admin_v1_router = APIRouter(prefix="/api/v1/admin", tags=["admin-v1"], dependencies=[Depends(api_key_auth)])

@admin_v1_router.get("/audits", summary="List Audit Logs", description="Retrieve audit logs with optional filtering by user_id, action, and pagination")
def list_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID (UUID)"),
    action: Optional[str] = Query(None, description="Filter by action type (e.g., 'grant', 'revoke')"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db)
):
    """List Audit Logs - Get all audit logs with optional filtering"""
    try:
        from sqlalchemy import desc
        from fastapi import HTTPException
        import uuid
        import traceback
        from app.models.audit import AuditLog
        
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
            error_details = traceback.format_exc()
            print(f"Query error in list_audit_logs (v1): {query_error}")
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
        print(f"Error in list_audit_logs (v1): {e}")
        print(error_details)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}. Check server logs for details.")

@admin_v1_router.get("/exports/{request_id}")
def get_export_details(request_id: str, db: Session = Depends(get_db)):
    """Get Export Details"""
    return {"request_id": request_id, "export_details": {}}

@admin_v1_router.get("/policy-snapshots")
def get_policy_snapshots_alt(
    region_code: Optional[str] = Query(None, description="Region code"),
    db: Session = Depends(get_db)
):
    """Get Policy Snapshots"""
    return {"snapshots": [], "region_code": region_code}

# Admin rights router
rights_router = APIRouter(prefix="/api/v1/admin", tags=["admin-rights"], dependencies=[Depends(api_key_auth)])

@rights_router.get("/deletions/{request_id}")
def get_deletion_details(request_id: str, db: Session = Depends(get_db)):
    """Get Deletion Details"""
    return {"request_id": request_id, "deletion_details": {}}

# Retention router
retention_router = APIRouter(prefix="/api/v1/admin/retention", tags=["admin-retention"], dependencies=[Depends(api_key_auth)])

@retention_router.post("/rules", status_code=201)
def create_retention_rule(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Retention Rule"""
    return {"message": "Retention rule created", "data": request}

@retention_router.get("/rules")
def list_retention_rules(db: Session = Depends(get_db)):
    """List Retention Rules"""
    return {"rules": []}

@retention_router.get("/jobs")
def list_retention_jobs(db: Session = Depends(get_db)):
    """List Retention Jobs"""
    return {"jobs": []}
