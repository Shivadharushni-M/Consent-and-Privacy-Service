import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base
from app.db.types import GUID, JSONBType
from app.models.consent import RegionEnum


class RetentionEntityTypeEnum(str, enum.Enum):
    CONSENT_RECORD = "ConsentRecord"
    AUDIT_LOG_ENTRY = "AuditLogEntry"
    RIGHTS_REQUEST = "RightsRequest"


class RetentionRule(Base):
    __tablename__ = "retention_rules"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    entity_type: Mapped[RetentionEntityTypeEnum] = mapped_column(
        String(50), nullable=False, index=True
    )
    retention_period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    applies_to_region: Mapped[Optional[RegionEnum]] = mapped_column(
        String(10), nullable=True, index=True
    )
    applies_to_legal_basis: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_retention_rule_entity", "entity_type", "applies_to_region"),
    )


class RetentionJobStatusEnum(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RetentionJob(Base):
    __tablename__ = "retention_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[RetentionJobStatusEnum] = mapped_column(
        String(20), nullable=False, default=RetentionJobStatusEnum.RUNNING
    )
    deleted_records_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    log: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)

    __table_args__ = (
        Index("idx_retention_job_status", "status", "started_at"),
    )
