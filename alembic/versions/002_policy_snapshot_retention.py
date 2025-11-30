"""add policy snapshot columns and audit nullable user

Revision ID: 002
Revises: 001
Create Date: 2025-11-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consent_history",
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
    )
    op.alter_column(
        "audit_logs",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("audit_logs", "policy_snapshot")
    op.drop_column("consent_history", "policy_snapshot")


