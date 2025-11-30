from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from app.db.database import get_db
from app.utils.security import api_key_auth

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"], dependencies=[Depends(api_key_auth)])

@router.post("", status_code=201)
def create_subject(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Subject"""
    return {"message": "Subject created", "data": request}

@router.get("/{subject_id}")
def get_subject(subject_id: str, db: Session = Depends(get_db)):
    """Get Subject"""
    return {"subject_id": subject_id, "message": "Subject retrieved"}

@router.patch("/{subject_id}")
def update_subject(subject_id: str, request: Dict[str, Any], db: Session = Depends(get_db)):
    """Update Subject"""
    return {"subject_id": subject_id, "message": "Subject updated", "data": request}

@router.delete("/{subject_id}")
def delete_subject(subject_id: str, db: Session = Depends(get_db)):
    """Delete Subject"""
    return {"subject_id": subject_id, "message": "Subject deleted"}

@router.get("/by-external/{external_id}")
def get_subject_by_external(
    external_id: str,
    tenant_id: Optional[str] = Query(None, description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get Subject By External"""
    return {"external_id": external_id, "tenant_id": tenant_id, "message": "Subject retrieved"}

@router.patch("/by-external/{external_id}")
def update_subject_by_external(
    external_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update Subject By External"""
    return {"external_id": external_id, "message": "Subject updated", "data": request}
