import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base
from app.db.types import GUID, JSONBType


class TokenPurposeEnum(str, enum.Enum):
    RIGHTS_EXPORT = "rights_export"
    RIGHTS_DELETION = "rights_deletion"
    RIGHTS_ACCESS = "rights_access"


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    purpose: Mapped[TokenPurposeEnum] = mapped_column(String(50), nullable=False, index=True)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_token_subject_purpose", "subject_id", "purpose"),
    )
