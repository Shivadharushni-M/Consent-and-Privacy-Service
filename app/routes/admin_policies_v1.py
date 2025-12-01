from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.policy import Policy, PolicyVersion
from app.schemas.policy import (
    PolicyCreate,
    PolicyResponse,
    PolicySnapshotQuery,
    PolicyVersionCreate,
    PolicyVersionResponse,
)
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/admin/policies",
    tags=["admin-policies"],
    dependencies=[Depends(api_key_auth)],
)


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED, summary="Create Policy", description="Create a new policy with the specified name, description, region code, and optional tenant ID")
def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    new_policy = Policy(
        tenant_id=policy.tenant_id,
        name=policy.name,
        description=policy.description,
        region_code=policy.region_code,
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy


@router.get("", response_model=List[PolicyResponse], summary="List Policies", description="Retrieve a list of policies, optionally filtered by region_code and/or tenant_id")
def list_policies(
    region_code: Optional[str] = Query(None, description="Filter by region code (e.g., EU, US, INDIA)"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    db: Session = Depends(get_db),
):
    query = db.query(Policy)
    if region_code:
        query = query.filter(Policy.region_code == region_code)
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    return query.all()


@router.post("/{policy_id}/versions", response_model=PolicyVersionResponse, status_code=status.HTTP_201_CREATED, summary="Create Policy Version", description="Create a new version for an existing policy with effective dates and policy matrix data")
def create_policy_version(
    policy_id: UUID,
    version: PolicyVersionCreate,
    db: Session = Depends(get_db),
):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    
    # Get next version number
    max_version = db.query(PolicyVersion.version_number).filter(
        PolicyVersion.policy_id == policy_id
    ).order_by(PolicyVersion.version_number.desc()).first()
    next_version = (max_version[0] if max_version else 0) + 1
    
    new_version = PolicyVersion(
        policy_id=policy_id,
        version_number=next_version,
        effective_from=version.effective_from,
        effective_to=version.effective_to,
        matrix=version.matrix,
        created_by=version.created_by,
    )
    db.add(new_version)
    policy.current_version_id = new_version.id
    db.commit()
    db.refresh(new_version)
    return new_version


@router.get("/{policy_id}/versions", response_model=List[PolicyVersionResponse], summary="List Policy Versions", description="Retrieve all versions for a specific policy")
def list_policy_versions(policy_id: UUID, db: Session = Depends(get_db)):
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return db.query(PolicyVersion).filter(PolicyVersion.policy_id == policy_id).all()


@router.get("/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse, summary="Get Policy Version", description="Retrieve a specific version of a policy by policy ID and version ID")
def get_policy_version(policy_id: UUID, version_id: UUID, db: Session = Depends(get_db)):
    version = db.get(PolicyVersion, version_id)
    if not version or version.policy_id != policy_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy version not found")
    return version


@router.get("/snapshots", response_model=List[PolicyVersionResponse], summary="Get Policy Snapshots", description="Retrieve policy snapshots (active policy versions) filtered by region, timestamp, and/or tenant. Returns policy versions that are effective at the specified timestamp (or current time if not specified)")
def get_policy_snapshots(
    region_code: Optional[str] = Query(None, description="Filter by region code (e.g., EU, US, INDIA)"),
    timestamp: Optional[datetime] = Query(None, description="Get snapshots effective at this timestamp (ISO 8601 format). If not provided, uses current time"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    db: Session = Depends(get_db),
):
    query = db.query(PolicyVersion).join(Policy)
    
    if region_code:
        query = query.filter(Policy.region_code == region_code)
    if tenant_id:
        query = query.filter(Policy.tenant_id == tenant_id)
    if timestamp:
        query = query.filter(
            PolicyVersion.effective_from <= timestamp,
            (PolicyVersion.effective_to.is_(None) | (PolicyVersion.effective_to > timestamp))
        )
    
    return query.all()
