"""add_user_api_key

Revision ID: 009
Revises: 008
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('api_key', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_api_key'), 'users', ['api_key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_api_key'), table_name='users')
    op.drop_column('users', 'api_key')

