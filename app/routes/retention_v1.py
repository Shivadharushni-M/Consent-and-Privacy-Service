from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/rules", response_model=RetentionRuleResponse, status_code=status.HTTP_201_CREATED)
def create_retention_rule(rule: RetentionRuleCreate, db: Session = Depends(get_db)):
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


@router.get("/rules", response_model=List[RetentionRuleResponse])
def list_retention_rules(
    tenant_id: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(RetentionRule)
    if tenant_id:
        query = query.filter(RetentionRule.tenant_id == tenant_id)
    return query.all()


@router.get("/jobs", response_model=List[RetentionJobResponse])
def list_retention_jobs(db: Session = Depends(get_db)):
    return db.query(RetentionJob).order_by(RetentionJob.started_at.desc()).all()
