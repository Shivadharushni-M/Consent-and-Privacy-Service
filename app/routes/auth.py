from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import AdminLoginRequest, LoginRequest, TokenResponse
from app.models.consent import User
from app.models.admin import Admin
from app.utils.security import create_jwt_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=200,
    description="Login as a user. Returns JWT token for user authentication."
)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or (user.password_hash and not verify_password(credentials.password, user.password_hash)) or (not user.password_hash and (not user.api_key or credentials.password != user.api_key)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    token = create_jwt_token(sub=user.id, role="user")
    return TokenResponse(access_token=token, user_id=user.id, role="user")


@router.post(
    "/admin/login",
    response_model=TokenResponse,
    status_code=200,
    description="Login as an admin. Returns JWT token for admin authentication."
)
def admin_login(credentials: AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.query(Admin).filter(Admin.email == credentials.email).first()
    if not admin or not verify_password(credentials.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    token = create_jwt_token(sub=admin.id, role="admin")
    return TokenResponse(access_token=token, user_id=admin.id, role="admin")
