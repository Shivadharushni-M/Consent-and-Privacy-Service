from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.jobs.retention import run_retention_cleanup
from app.utils.security import AuthenticatedActor, require_admin

router = APIRouter(prefix="/retention", tags=["retention"])


@router.get(
    "/run",
    description="Trigger retention cleanup job. Admin JWT token required."
)
def trigger_retention_cleanup(db: Session = Depends(get_db), actor: AuthenticatedActor = Depends(require_admin)):
    return run_retention_cleanup(db)
