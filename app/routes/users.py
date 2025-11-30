from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.db.database import get_db
from app.utils.security import api_key_auth
from app.schemas.common import UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(api_key_auth)])

@router.post("", status_code=201)
def create_user(request: UserCreateRequest, db: Session = Depends(get_db)):
    """Create User"""
    try:
        return {
            "message": "User created",
            "user_id": request.user_id,
            "email": request.email,
            "name": request.name,
            "metadata": request.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get User"""
    return {"user_id": user_id, "message": "User retrieved"}

@router.patch("/{user_id}")
def update_user(user_id: str, request: UserUpdateRequest, db: Session = Depends(get_db)):
    """Update User"""
    try:
        return {
            "user_id": user_id,
            "message": "User updated",
            "email": request.email,
            "name": request.name,
            "metadata": request.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
