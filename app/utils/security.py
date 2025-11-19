from itsdangerous import URLSafeTimedSerializer
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

