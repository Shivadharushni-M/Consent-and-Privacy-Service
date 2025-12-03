from datetime import datetime, timezone
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory, RegionEnum
from app.schemas.policy import PolicySnapshotResponse
from app.utils.security import api_key_auth

router = APIRouter(prefix="/admin/policies", tags=["admin"], dependencies=[Depends(api_key_auth)])


@router.get("/snapshots", response_model=List[PolicySnapshotResponse])
def get_policy_snapshots(
    region_code: Optional[str] = Query(None),
    timestamp: Optional[datetime] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    now = timestamp or datetime.now(timezone.utc)
    consent_query = db.query(ConsentHistory.policy_snapshot, ConsentHistory.region, ConsentHistory.tenant_id, ConsentHistory.timestamp).filter(ConsentHistory.policy_snapshot.isnot(None))
    audit_query = db.query(AuditLog.policy_snapshot, AuditLog.tenant_id, AuditLog.event_time.label("timestamp")).filter(AuditLog.policy_snapshot.isnot(None))
    if region_code:
        try:
            region_enum = RegionEnum(region_code)
            consent_query = consent_query.filter(ConsentHistory.region == region_enum)
            audit_query = audit_query.filter(AuditLog.policy_snapshot.op("->>")("region") == region_code)
        except ValueError:
            return []
    if tenant_id:
        consent_query = consent_query.filter(ConsentHistory.tenant_id == tenant_id)
        audit_query = audit_query.filter(AuditLog.tenant_id == tenant_id)
    if timestamp:
        consent_query = consent_query.filter(ConsentHistory.timestamp <= timestamp)
        audit_query = audit_query.filter(AuditLog.event_time <= timestamp)
    consent_results = consent_query.all()
    audit_results = audit_query.all()
    seen_snapshots: Set[str] = set()
    unique_snapshots: List[PolicySnapshotResponse] = []
    for row in consent_results:
        if row.policy_snapshot:
            snapshot_key = str(sorted(row.policy_snapshot.items()))
            if snapshot_key not in seen_snapshots:
                seen_snapshots.add(snapshot_key)
                unique_snapshots.append(PolicySnapshotResponse(snapshot=row.policy_snapshot, region=row.region.value if row.region else None, tenant_id=row.tenant_id, timestamp=row.timestamp, source="consent_history"))
    for row in audit_results:
        if row.policy_snapshot:
            snapshot_key = str(sorted(row.policy_snapshot.items()))
            if snapshot_key not in seen_snapshots:
                seen_snapshots.add(snapshot_key)
                unique_snapshots.append(PolicySnapshotResponse(snapshot=row.policy_snapshot, region=row.policy_snapshot.get("region") if isinstance(row.policy_snapshot, dict) else None, tenant_id=row.tenant_id, timestamp=row.timestamp, source="audit_logs"))
    return unique_snapshots
