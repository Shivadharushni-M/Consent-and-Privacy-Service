"""add_withdrawn_expired_to_status_enum

Revision ID: 007
Revises: 006
Create Date: 2025-11-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'withdrawn' and 'expired' values to status_enum
    # Check if values exist first, then add if they don't
    conn = op.get_bind()
    
    # Check current enum values
    result = conn.execute(text("""
        SELECT enumlabel 
        FROM pg_enum 
        WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'status_enum')
    """))
    existing_values = {row[0] for row in result}
    
    # Add 'withdrawn' if it doesn't exist
    if 'withdrawn' not in existing_values:
        op.execute(text("ALTER TYPE status_enum ADD VALUE 'withdrawn'"))
    
    # Add 'expired' if it doesn't exist
    if 'expired' not in existing_values:
        op.execute(text("ALTER TYPE status_enum ADD VALUE 'expired'"))


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum values in place
    pass
