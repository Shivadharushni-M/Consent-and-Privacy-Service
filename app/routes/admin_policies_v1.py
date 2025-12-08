from typing import List, Set
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.audit import AuditLog
from app.models.consent import ConsentHistory
from app.schemas.policy import PolicySnapshotResponse
from app.utils.security import AuthenticatedActor, require_admin

router = APIRouter(prefix="/admin/policies", tags=["admin"])


@router.get(
    "/snapshots",
    response_model=List[PolicySnapshotResponse],
    description="Get all policy snapshots. Admin JWT token required."
)
def get_policy_snapshots(
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_admin),
):
    consent_query = db.query(ConsentHistory.policy_snapshot, ConsentHistory.region, ConsentHistory.tenant_id, ConsentHistory.timestamp).filter(ConsentHistory.policy_snapshot.isnot(None))
    audit_query = db.query(AuditLog.policy_snapshot, AuditLog.tenant_id, AuditLog.event_time.label("timestamp")).filter(AuditLog.policy_snapshot.isnot(None))
    
    def _get_snapshot_key(snapshot) -> str:
        return str(sorted(snapshot.items())) if isinstance(snapshot, dict) else str(snapshot)
    
    def _process_snapshot_row(row, source: str):
        if not row.policy_snapshot:
            return None, None
        key = _get_snapshot_key(row.policy_snapshot)
        region_val = row.region.value if hasattr(row, 'region') and row.region else (row.policy_snapshot.get("region") if isinstance(row.policy_snapshot, dict) else None)
        return key, PolicySnapshotResponse(snapshot=row.policy_snapshot, region=region_val, tenant_id=row.tenant_id, timestamp=row.timestamp, source=source)
    
    seen_snapshots: Set[str] = set()
    unique_snapshots: List[PolicySnapshotResponse] = []
    for row in consent_query.all() + audit_query.all():
        key, snapshot = _process_snapshot_row(row, "consent_history" if hasattr(row, 'region') else "audit_logs")
        if key and snapshot and key not in seen_snapshots:
            seen_snapshots.add(key)
            unique_snapshots.append(snapshot)
    return unique_snapshots
