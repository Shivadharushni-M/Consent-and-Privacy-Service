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


@router.get("/run")
def trigger_retention_cleanup(db: Session = Depends(get_db)):
    """Trigger the retention cleanup job manually."""
    return run_retention_cleanup(db)
