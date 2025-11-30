from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.database import get_db
from app.utils.security import api_key_auth

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"], dependencies=[Depends(api_key_auth)])

@router.post("", status_code=201)
def create_decision(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create Decision"""
    return {"message": "Decision created", "data": request}
