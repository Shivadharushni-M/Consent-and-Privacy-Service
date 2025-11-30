from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.catalog import Purpose, PurposeGroup, Vendor
from app.schemas.catalog import (
    PurposeCreate,
    PurposeGroupCreate,
    PurposeGroupResponse,
    PurposeResponse,
    PurposeUpdate,
    VendorCreate,
    VendorResponse,
)
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-catalog"],
    dependencies=[Depends(api_key_auth)],
)


# Purposes
@router.post("/purposes", response_model=PurposeResponse, status_code=status.HTTP_201_CREATED)
def create_purpose(purpose: PurposeCreate, db: Session = Depends(get_db)):
    try:
        new_purpose = Purpose(
            tenant_id=purpose.tenant_id,
            code=purpose.code,
            name=purpose.name,
            description=purpose.description,
            purpose_group_id=purpose.purpose_group_id,
        )
        db.add(new_purpose)
        db.commit()
        db.refresh(new_purpose)
        return new_purpose
    except IntegrityError as exc:
        db.rollback()
        if "code" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Purpose with code '{purpose.code}' already exists"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create purpose"
        ) from exc


@router.get("/purposes", response_model=List[PurposeResponse])
def list_purposes(
    tenant_id: Optional[str] = None,
    active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Purpose)
    if tenant_id:
        query = query.filter(Purpose.tenant_id == tenant_id)
    if active is not None:
        query = query.filter(Purpose.active == active)
    return query.all()


@router.patch("/purposes/{purpose_id}", response_model=PurposeResponse)
def update_purpose(
    purpose_id: UUID,
    payload: PurposeUpdate,
    db: Session = Depends(get_db),
):
    purpose = db.get(Purpose, purpose_id)
    if not purpose:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purpose not found")
    
    if payload.name is not None:
        purpose.name = payload.name
    if payload.description is not None:
        purpose.description = payload.description
    if payload.purpose_group_id is not None:
        purpose.purpose_group_id = payload.purpose_group_id
    if payload.active is not None:
        purpose.active = payload.active
    
    db.commit()
    db.refresh(purpose)
    return purpose


# Purpose Groups
@router.post("/purpose-groups", response_model=PurposeGroupResponse, status_code=status.HTTP_201_CREATED)
def create_purpose_group(group: PurposeGroupCreate, db: Session = Depends(get_db)):
    try:
        new_group = PurposeGroup(
            tenant_id=group.tenant_id,
            code=group.code,
            name=group.name,
            description=group.description,
            precedence=group.precedence,
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        return new_group
    except IntegrityError as exc:
        db.rollback()
        if "code" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Purpose group with code '{group.code}' already exists"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create purpose group"
        ) from exc


@router.get("/purpose-groups", response_model=List[PurposeGroupResponse])
def list_purpose_groups(
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(PurposeGroup)
    if tenant_id:
        query = query.filter(PurposeGroup.tenant_id == tenant_id)
    return query.order_by(PurposeGroup.precedence).all()


# Vendors
@router.post("/vendors", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
def create_vendor(vendor: VendorCreate, db: Session = Depends(get_db)):
    try:
        new_vendor = Vendor(
            tenant_id=vendor.tenant_id,
            code=vendor.code,
            name=vendor.name,
            relationship_type=vendor.relationship_type,
            dpa_url=vendor.dpa_url,
        )
        db.add(new_vendor)
        db.commit()
        db.refresh(new_vendor)
        return new_vendor
    except IntegrityError as exc:
        db.rollback()
        if "code" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vendor with code '{vendor.code}' already exists"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create vendor"
        ) from exc


@router.get("/vendors", response_model=List[VendorResponse])
def list_vendors(
    tenant_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Vendor)
    if tenant_id:
        query = query.filter(Vendor.tenant_id == tenant_id)
    return query.all()
