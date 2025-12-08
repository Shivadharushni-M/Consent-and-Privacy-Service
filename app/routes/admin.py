import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.admin import Admin
from app.models.audit import AuditLog
from app.models.consent import PurposeEnum, RegionEnum
from app.schemas.auth import AdminCreateRequest, AdminCreateResponse
from app.schemas.consent import AuditLogResponse
from app.utils.security import AuthenticatedActor, get_optional_actor, hash_password, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/audit",
    response_model=List[AuditLogResponse],
    description="List audit logs with optional filters. Admin JWT token required."
)
def list_audit_logs(
    user_id: Optional[str] = Query(None),
    purpose: Optional[PurposeEnum] = Query(None),
    region: Optional[RegionEnum] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_admin),
):
    query = db.query(AuditLog)
    if user_id:
        try:
            query = query.filter(AuditLog.user_id == uuid.UUID(user_id))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id format. Must be a valid UUID.")
    if purpose:
        query = query.filter(text("details->>'purpose' = :purpose")).params(purpose=purpose.value)
    if region:
        query = query.filter(text("details->>'region' = :region")).params(region=region.value)
    logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    for log in logs:
        if log.details is None:
            log.details = {}
    return logs


@router.post(
    "/admins",
    response_model=AdminCreateResponse,
    status_code=status.HTTP_201_CREATED,
    description="Create a new admin user. Admin JWT token required - only existing admins can create new admins. If no admins exist, this endpoint allows creating the first admin without authentication (bootstrap mode)."
)
def create_admin(
    admin_data: AdminCreateRequest,
    db: Session = Depends(get_db),
    actor: Optional[AuthenticatedActor] = Depends(get_optional_actor),
):
    admin_count = db.query(Admin).count()
    if admin_count > 0 and (not actor or actor.role != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    if db.query(Admin).filter(Admin.email == admin_data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="admin_email_already_exists")
    new_admin = Admin(email=admin_data.email, password_hash=hash_password(admin_data.password))
    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return AdminCreateResponse(id=new_admin.id, email=new_admin.email, created_at=new_admin.created_at.isoformat())
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="admin_email_already_exists")
