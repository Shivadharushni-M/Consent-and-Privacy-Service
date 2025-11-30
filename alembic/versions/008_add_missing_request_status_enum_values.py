"""add_missing_request_status_enum_values

Revision ID: 008
Revises: 007
Create Date: 2025-11-30 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing values to request_status_enum
    # Check if values exist first, then add if they don't
    conn = op.get_bind()
    
    # Check current enum values
    result = conn.execute(text("""
        SELECT enumlabel 
        FROM pg_enum 
        WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'request_status_enum')
    """))
    existing_values = {row[0] for row in result}
    
    # Add missing values
    missing_values = [
        'pending_verification',
        'verified',
        'processing',
        'cancelled'
    ]
    
    for value in missing_values:
        if value not in existing_values:
            op.execute(text(f"ALTER TYPE request_status_enum ADD VALUE '{value}'"))


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the enum values in place
    pass

