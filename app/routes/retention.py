from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.retention import run_retention_cleanup
from app.utils.security import api_key_auth

router = APIRouter(
    prefix="/retention",
    tags=["retention"],
    dependencies=[Depends(api_key_auth)],
)


@router.get("/run", summary="Trigger Retention Cleanup", description="Manually trigger the retention cleanup job")
def trigger_retention_cleanup(db: Session = Depends(get_db)):
    """Trigger Retention Cleanup - Manually run the retention cleanup job"""
    return run_retention_cleanup(db)
