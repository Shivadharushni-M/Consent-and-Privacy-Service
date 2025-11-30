from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, String
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


@router.get("/audit", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = Query(default=None),
    purpose: Optional[PurposeEnum] = Query(default=None),
    region: Optional[RegionEnum] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if purpose:
        query = query.filter(cast(AuditLog.details["purpose"], String) == purpose.value)
    if region:
        query = query.filter(cast(AuditLog.details["region"], String) == region.value)
    return query.order_by(AuditLog.created_at.desc()).all()


@router.get("/subject-requests", response_model=List[SubjectRequestResponse])
def list_subject_requests(db: Session = Depends(get_db)):
    return (
        db.query(SubjectRequest)
        .order_by(SubjectRequest.requested_at.desc())
        .all()
    )


