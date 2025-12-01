"""add expiry and verification token

Revision ID: 003
Revises: 002
Create Date: 2025-01-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Check if expires_at column already exists in consent_history
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'consent_history' AND column_name = 'expires_at'
    """))
    expires_at_exists = result.fetchone() is not None
    
    if not expires_at_exists:
        op.add_column(
            "consent_history",
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            op.f("ix_consent_history_expires_at"), "consent_history", ["expires_at"], unique=False
        )
    
    # Check if verification_token column already exists in subject_requests
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'subject_requests' AND column_name = 'verification_token'
    """))
    verification_token_exists = result.fetchone() is not None
    
    if not verification_token_exists:
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

