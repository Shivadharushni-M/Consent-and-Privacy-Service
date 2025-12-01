from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.retention import RetentionJob, RetentionRule
from app.schemas.retention import RetentionJobResponse, RetentionRuleCreate, RetentionRuleResponse
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/api/v1/admin/retention",
    tags=["admin-retention"],
    dependencies=[Depends(api_key_auth)],
)


@router.post(
    "/rules",
    response_model=RetentionRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Retention Rule",
    description="Create a new retention rule that defines how long data should be retained before deletion"
)
def create_retention_rule(rule: RetentionRuleCreate, db: Session = Depends(get_db)):
    """
    Create a new retention rule.
    
    **Request Body Example:**
    ```json
    {
        "entity_type": "ConsentRecord",
        "retention_period_days": 365,
        "applies_to_region": "EU",
        "applies_to_legal_basis": "consent",
        "tenant_id": "tenant-123"
    }
    ```
    
    - **entity_type**: Type of entity to apply retention to (ConsentRecord, AuditLogEntry, RightsRequest)
    - **retention_period_days**: Number of days to retain data before deletion
    - **applies_to_region**: Optional region code (e.g., "EU", "US")
    - **applies_to_legal_basis**: Optional legal basis filter
    - **tenant_id**: Optional tenant ID for multi-tenant scenarios
    """
    new_rule = RetentionRule(
        tenant_id=rule.tenant_id,
        entity_type=rule.entity_type,
        retention_period_days=rule.retention_period_days,
        applies_to_region=rule.applies_to_region,
        applies_to_legal_basis=rule.applies_to_legal_basis,
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule


@router.get(
    "/rules",
    response_model=List[RetentionRuleResponse],
    summary="List Retention Rules",
    description="Retrieve a list of all retention rules, optionally filtered by tenant_id"
)
def list_retention_rules(
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID to filter rules"),
    db: Session = Depends(get_db),
):
    """
    List all retention rules.
    
    **Query Parameters:**
    - **tenant_id** (optional): Filter rules by tenant ID
    
    Returns a list of all retention rules matching the criteria.
    """
    query = db.query(RetentionRule)
    if tenant_id:
        query = query.filter(RetentionRule.tenant_id == tenant_id)
    return query.all()


@router.get(
    "/jobs",
    response_model=List[RetentionJobResponse],
    summary="List Retention Jobs",
    description="Retrieve a list of all retention job execution records, ordered by most recent first"
)
def list_retention_jobs(db: Session = Depends(get_db)):
    """
    List all retention job execution records.
    
    Returns a list of retention jobs showing execution history, status, and deletion counts.
    Jobs are ordered by start time (most recent first).
    """
    return db.query(RetentionJob).order_by(RetentionJob.started_at.desc()).all()
