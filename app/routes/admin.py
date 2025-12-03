import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, desc
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import PurposeEnum, RegionEnum
from app.schemas.consent import AuditLogResponse
from app.utils.security import api_key_auth

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(api_key_auth)])


@router.get("/audit", response_model=List[AuditLogResponse])
def list_audit_logs(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    purpose: Optional[PurposeEnum] = Query(None),
    region: Optional[RegionEnum] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if user_id:
        try:
            query = query.filter(AuditLog.user_id == uuid.UUID(user_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format. Must be a valid UUID.")
    if action:
        query = query.filter(AuditLog.action == action)
    if purpose:
        query = query.filter(cast(AuditLog.details["purpose"], String) == purpose.value)
    if region:
        query = query.filter(cast(AuditLog.details["region"], String) == region.value)
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    for log in logs:
        if log.details is None:
            log.details = {}
    return logs
