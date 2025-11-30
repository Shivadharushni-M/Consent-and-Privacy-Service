from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.consent import RegionEnum
from app.schemas.subject import SubjectCreate, SubjectResponse, SubjectUpdate
from app.services import subject_service
from app.services.region_service import detect_region_from_ip
from app.utils.helpers import extract_client_ip
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/subjects",
    tags=["subjects"],
    dependencies=[Depends(api_key_auth)],
)


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject: SubjectCreate,
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
):
    try:
        # Auto-detect region if not provided
        region = subject.region_code
        if not region:
            client_ip = extract_client_ip(request)
            # Use the same detection logic as the /region endpoint
            # This ensures consistency between GET /region and POST /subjects
            region = detect_region_from_ip(client_ip)
        else:
            # Validate region_code if provided
            from app.utils.helpers import validate_region
            region = validate_region(region)
        
        user = subject_service.get_or_create_subject(
            db=db,
            external_id=subject.external_id,
            identifier_type=subject.identifier_type,
            identifier_value=subject.identifier_value,
            region_code=region,
            tenant_id=subject.tenant_id,
        )
        return user
    except ValueError as exc:
        if str(exc) == "duplicate_subject":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subject already exists") from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: UUID, db: Session = Depends(get_db)):
    try:
        from app.services.user_service import get_user
        return get_user(db, subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found") from exc


@router.get("/by-external/{external_id}", response_model=SubjectResponse)
def get_subject_by_external(
    external_id: str,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    try:
        return subject_service.get_subject_by_external_id(db, external_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found") from exc


@router.patch("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: UUID,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
):
    try:
        # Region is auto-detected and cannot be manually updated
        return subject_service.update_subject(
            db=db,
            subject_id=subject_id,
            identifier_type=payload.identifier_type,
            identifier_value=payload.identifier_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found") from exc


@router.patch("/by-external/{external_id}", response_model=SubjectResponse)
def update_subject_by_external(
    external_id: str,
    payload: SubjectUpdate,
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update subject by external_id instead of UUID."""
    try:
        # First get the subject by external_id to get the UUID
        user = subject_service.get_subject_by_external_id(db, external_id, tenant_id)
        # Then update using the UUID
        return subject_service.update_subject(
            db=db,
            subject_id=user.id,
            identifier_type=payload.identifier_type,
            identifier_value=payload.identifier_value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found") from exc


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: UUID, db: Session = Depends(get_db)):
    try:
        subject_service.delete_subject(db, subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found") from exc
