from fastapi import APIRouter, Depends
from app.utils.security import api_key_auth

router = APIRouter(prefix="/api/v1", tags=["version"], dependencies=[Depends(api_key_auth)])

@router.get("/version")
def get_version():
    """Get Version"""
    return {"version": "1.0.0", "service": "Consent & Privacy Preferences Service"}

@router.get("/health")
def health_check():
    """Health Check"""
    return {"status": "healthy", "service": "Consent & Privacy Preferences Service"}
