import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base
from app.db.types import GUID


class PurposeEnum(str, enum.Enum):
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    PERSONALIZATION = "personalization"
    DATA_SHARING = "data_sharing"


class StatusEnum(str, enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"


class RegionEnum(str, enum.Enum):
    EU = "EU"
    US = "US"
    IN = "IN"
    BR = "BR"
    SG = "SG"
    AU = "AU"
    JP = "JP"
    CA = "CA"
    UK = "UK"
    ZA = "ZA"
    KR = "KR"


class RetentionEntityEnum(str, enum.Enum):
    CONSENT = "consent"
    AUDIT = "audit"
    USER = "user"


class RequestTypeEnum(str, enum.Enum):
    ACCESS = "access"
    DELETE = "delete"
    EXPORT = "export"
    RECTIFY = "rectify"


class RequestStatusEnum(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    region: Mapped[RegionEnum] = mapped_column(
        SQLEnum(RegionEnum, name="region_enum"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    consent_history: Mapped[List["ConsentHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subject_requests: Mapped[List["SubjectRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ConsentHistory(Base):
    __tablename__ = "consent_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[PurposeEnum] = mapped_column(
        SQLEnum(PurposeEnum, name="purpose_enum"), nullable=False, index=True
    )
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum, name="status_enum"), nullable=False
    )
    region: Mapped[RegionEnum] = mapped_column(
        SQLEnum(RegionEnum, name="region_enum"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped["User"] = relationship(back_populates="consent_history")

    __table_args__ = (
        Index("idx_user_purpose", "user_id", "purpose"),
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class RetentionSchedule(Base):
    __tablename__ = "retention_schedules"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[RetentionEntityEnum] = mapped_column(
        SQLEnum(RetentionEntityEnum, name="retention_entity_enum"),
        nullable=False,
        unique=True,
        index=True,
    )
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SubjectRequest(Base):
    __tablename__ = "subject_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_type: Mapped[RequestTypeEnum] = mapped_column(
        SQLEnum(RequestTypeEnum, name="request_type_enum"), nullable=False, index=True
    )
    status: Mapped[RequestStatusEnum] = mapped_column(
        SQLEnum(RequestStatusEnum, name="request_status_enum"),
        nullable=False,
        default=RequestStatusEnum.PENDING,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="subject_requests")

    __table_args__ = (Index("idx_user_request_type", "user_id", "request_type"),)

