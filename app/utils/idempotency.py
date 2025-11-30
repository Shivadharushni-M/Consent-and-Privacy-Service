import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base
from app.utils.helpers import get_utc_now


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    response_data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


def hash_idempotency_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def get_cached_response(db, key: str) -> Optional[Dict]:
    key_hash = hash_idempotency_key(key)
    record = db.query(IdempotencyKey).filter(
        IdempotencyKey.key_hash == key_hash,
        IdempotencyKey.expires_at > get_utc_now()
    ).first()
    if record:
        import json
        return json.loads(record.response_data)
    return None


def cache_response(db, key: str, response_data: Dict, ttl_seconds: int = 3600):
    key_hash = hash_idempotency_key(key)
    expires_at = get_utc_now() + timedelta(seconds=ttl_seconds)
    import json
    record = IdempotencyKey(
        key_hash=key_hash,
        response_data=json.dumps(response_data),
        expires_at=expires_at
    )
    db.merge(record)
    db.commit()
