"""add_ads_to_purpose_enum

Revision ID: 06cc4d717681
Revises: 011
Create Date: 2025-12-08 12:46:43.934020

"""
from alembic import op
import sqlalchemy as sa


revision = '06cc4d717681'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'ads'")
    op.execute("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'email'")
    op.execute("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'location'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values, so we can't downgrade
    pass

