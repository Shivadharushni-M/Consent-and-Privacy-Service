from itsdangerous import URLSafeTimedSerializer
from fastapi import Header, HTTPException, status

from app.config import settings


def create_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY)


def generate_verification_token(data: dict) -> str:
    serializer = create_serializer()
    return serializer.dumps(data, salt=settings.ALGORITHM)


def verify_token(token: str, max_age: int = 3600) -> dict:
    serializer = create_serializer()
    try:
        data = serializer.loads(token, salt=settings.ALGORITHM, max_age=max_age)
        return data
    except Exception:
        return None


def api_key_auth(x_api_key: str = Header(default=None, alias="X-API-Key")) -> str:
    expected_key = settings.API_KEY
    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="api_key_not_configured",
        )
    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key"
        )
    return expected_key

