import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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
from app.db.types import GUID, JSONBType


class PurposeEnum(str, enum.Enum):
    ANALYTICS = "analytics"
    ADS = "ads"
    EMAIL = "email"
    LOCATION = "location"
    MARKETING = "marketing"
    PERSONALIZATION = "personalization"
    DATA_SHARING = "data_sharing"


class VendorEnum(str, enum.Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    TWILIO = "twilio"
    STRIPE = "stripe"
    AWS = "aws"
    AZURE = "azure"


class EventNameEnum(str, enum.Enum):
    PAGE_VIEW = "page_view"
    PURCHASE = "purchase"
    SIGNUP = "signup"
    AD_CLICK = "ad_click"
    NEWSLETTER_OPEN = "newsletter_open"
    LOCATION_PING = "location_ping"


class StatusEnum(str, enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class RegionEnum(str, enum.Enum):
    EU = "EU"
    US = "US"
    INDIA = "INDIA"
    ROW = "ROW"
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
    PENDING_VERIFICATION = "pending_verification"
    VERIFIED = "verified"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    primary_identifier_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    primary_identifier_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    region: Mapped[RegionEnum] = mapped_column(
        SQLEnum(RegionEnum, name="region_enum", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
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
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    consent_history: Mapped[List["ConsentHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subject_requests: Mapped[List["SubjectRequest"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    vendor_consents: Mapped[List["VendorConsent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class LegalBasisEnum(str, enum.Enum):
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGITIMATE_INTEREST = "legitimate_interest"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGAL_OBLIGATION = "legal_obligation"


class ConsentHistory(Base):
    __tablename__ = "consent_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose: Mapped[PurposeEnum] = mapped_column(
        SQLEnum(PurposeEnum, name="purpose_enum", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    legal_basis: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum, name="status_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    region: Mapped[RegionEnum] = mapped_column(
        SQLEnum(RegionEnum, name="region_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    granted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    valid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    policy_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True, index=True)
    policy_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType, nullable=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONBType, nullable=True)

    user: Mapped["User"] = relationship(back_populates="consent_history")

    __table_args__ = (
        Index("idx_user_purpose", "user_id", "purpose"),
        Index("idx_user_timestamp", "user_id", "timestamp"),
    )


class RetentionSchedule(Base):
    __tablename__ = "retention_schedules"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[RetentionEntityEnum] = mapped_column(
        SQLEnum(RetentionEntityEnum, name="retention_entity_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        unique=True,
        index=True,
    )
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SubjectRequest(Base):
    __tablename__ = "subject_requests"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_type: Mapped[RequestTypeEnum] = mapped_column(
        SQLEnum(RequestTypeEnum, name="request_type_enum", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    status: Mapped[RequestStatusEnum] = mapped_column(
        SQLEnum(RequestStatusEnum, name="request_status_enum", values_callable=lambda x: [e.value for e in x]),
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
    verification_token_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID, ForeignKey("verification_tokens.id"), nullable=True, index=True
    )
    result_location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    requested_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    user: Mapped["User"] = relationship(back_populates="subject_requests")

    __table_args__ = (Index("idx_user_request_type", "user_id", "request_type"),)


class VendorConsent(Base):
    __tablename__ = "vendor_consents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor: Mapped[VendorEnum] = mapped_column(
        SQLEnum(VendorEnum, name="vendor_enum", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    purpose: Mapped[PurposeEnum] = mapped_column(
        SQLEnum(PurposeEnum, name="purpose_enum", values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum, name="status_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    region: Mapped[RegionEnum] = mapped_column(
        SQLEnum(RegionEnum, name="region_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    policy_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONBType, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="vendor_consents")

    __table_args__ = (
        Index("idx_user_vendor_purpose", "user_id", "vendor", "purpose"),
        Index("idx_user_vendor_timestamp", "user_id", "vendor", "timestamp"),
    )
