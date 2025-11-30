import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base
from app.db.types import GUID, JSONBType


class ActorTypeEnum(str, enum.Enum):
    SYSTEM = "system"
    ADMIN = "admin"
    SUBJECT = "subject"


class EventTypeEnum(str, enum.Enum):
    CONSENT_GRANTED = "consent_granted"
    CONSENT_WITHDRAWN = "consent_withdrawn"
    CONSENT_DENIED = "consent_denied"
    DECISION_EVALUATED = "decision_evaluated"
    POLICY_CHANGED = "policy_changed"
    EXPORT_REQUESTED = "export_requested"
    DELETION_STARTED = "deletion_started"
    DELETION_COMPLETED = "deletion_completed"
    EXPORT_COMPLETED = "export_completed"
    RETENTION_RUN = "retention_run"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSONBType, nullable=False)
    policy_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType, nullable=True
    )
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (Index("idx_audit_user_created", "user_id", "created_at"),)

