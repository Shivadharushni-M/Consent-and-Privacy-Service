from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer
import jwt
from passlib.context import CryptContext
from app.config import settings
from app.db.database import get_db
from app.models.consent import User
from app.models.admin import Admin


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def generate_verification_token(data: dict) -> str:
    return create_serializer().dumps(data, salt=settings.ALGORITHM)


def verify_token(token: str, max_age: int = 3600) -> Optional[dict]:
    try:
        return create_serializer().loads(token, salt=settings.ALGORITHM, max_age=max_age)
    except Exception:
        return None


class Actor:
    def __init__(self, id: UUID, role: str, user: Optional[User] = None, admin: Optional[Admin] = None):
        self.id = id
        self.role = role
        self.user = user
        self.admin = admin
        self.actor_type = "user" if role == "user" else "admin"
    def __repr__(self):
        return f"Actor(id={self.id}, role={self.role})"


security_scheme = HTTPBearer(auto_error=False, scheme_name="HTTPBearer")


def create_jwt_token(sub: UUID, role: str) -> str:
    from datetime import timezone
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(sub), "role": role, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_jwt_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_bearer_token(authorization: Optional[str] = None) -> Optional[str]:
    if not authorization:
        return None
    auth_str = authorization.strip()
    return auth_str[7:].strip() if auth_str.startswith("Bearer ") else auth_str


def _truncate_password_bytes(password: str) -> bytes:
    password_bytes = password.encode('utf-8')
    return password_bytes[:72] if len(password_bytes) > 72 else password_bytes


def hash_password(password: str) -> str:
    password_bytes = _truncate_password_bytes(password)
    try:
        return pwd_context.hash(password_bytes.decode('utf-8', errors='ignore'))
    except (ValueError, AttributeError):
        import bcrypt
        return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, AttributeError):
        import bcrypt
        password_bytes = _truncate_password_bytes(plain_password)
        try:
            return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
        except Exception:
            return False


def _extract_bearer_token(request: Request, credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if credentials and credentials.credentials:
        return credentials.credentials
    for header_name in ["Authorization", "authorization", "AUTHORIZATION"]:
        if header_name in request.headers:
            token = get_bearer_token(request.headers[header_name])
            if token:
                return token
    for header_tuple in request.scope.get("headers", []):
        header_key = header_tuple[0].decode("utf-8").lower() if isinstance(header_tuple[0], bytes) else header_tuple[0].lower()
        if header_key == "authorization":
            auth_header = header_tuple[1].decode("utf-8") if isinstance(header_tuple[1], bytes) else header_tuple[1]
            token = get_bearer_token(auth_header)
            if token:
                return token
    return None


def _load_actor_from_token(payload: dict, db: Session) -> Actor:
    sub = UUID(payload["sub"])
    role = payload.get("role", "user")
    if role == "admin":
        admin = db.query(Admin).filter(Admin.id == sub).first()
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_not_found")
        return Actor(id=sub, role="admin", admin=admin)
    elif role == "user":
        user = db.query(User).filter(User.id == sub).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
        return Actor(id=sub, role="user", user=user)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_role")


def get_current_actor(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> Actor:
    bearer_token = _extract_bearer_token(request, credentials)
    if not bearer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_authorization_header")
    payload = decode_jwt_token(bearer_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_or_expired_token")
    return _load_actor_from_token(payload, db)


def require_admin(actor: Actor = Depends(get_current_actor)) -> Actor:
    if actor.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return actor


def validate_user_action(actor: Actor, user_id: UUID) -> None:
    if actor.role == "admin":
        return
    if actor.role == "user" and actor.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="user_id_mismatch")


AuthenticatedActor = Actor

def get_optional_actor(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[Actor]:
    bearer_token = _extract_bearer_token(request, credentials)
    if not bearer_token:
        return None
    payload = decode_jwt_token(bearer_token)
    if not payload:
        return None
    try:
        return _load_actor_from_token(payload, db)
    except HTTPException:
        return None
