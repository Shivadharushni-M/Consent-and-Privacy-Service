from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.utils.security import api_key_auth

router = APIRouter(prefix="/decision", tags=["decision"], dependencies=[Depends(api_key_auth)])

@router.get("")
def get_decision(
    user_id: Optional[str] = Query(None, description="User ID"),
    purpose: Optional[str] = Query(None, description="Purpose")
):
    """Get Decision"""
    return {"decision": "granted", "user_id": user_id, "purpose": purpose}
