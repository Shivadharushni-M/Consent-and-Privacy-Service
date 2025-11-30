"""add expiry and verification token

Revision ID: 003
Revises: 002
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consent_history",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_consent_history_expires_at"), "consent_history", ["expires_at"], unique=False
    )
    op.add_column(
        "subject_requests",
        sa.Column("verification_token", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_subject_requests_verification_token"),
        "subject_requests",
        ["verification_token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subject_requests_verification_token"), table_name="subject_requests")
    op.drop_column("subject_requests", "verification_token")
    op.drop_index(op.f("ix_consent_history_expires_at"), table_name="consent_history")
    op.drop_column("consent_history", "expires_at")

