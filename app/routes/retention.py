from fastapi import APIRouter, Depends
from app.utils.security import api_key_auth

router = APIRouter(prefix="/retention", tags=["retention"], dependencies=[Depends(api_key_auth)])

@router.get("/run")
def trigger_retention_cleanup():
    """Trigger Retention Cleanup"""
    return {"message": "Retention cleanup triggered", "status": "running"}
