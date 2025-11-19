"""initial schema

Revision ID: 001
Revises: 
Create Date: 2025-11-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('consent_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('purpose', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('region', sa.String(length=50), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('policy_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consent_history_id'), 'consent_history', ['id'], unique=False)
    op.create_index(op.f('ix_consent_history_purpose'), 'consent_history', ['purpose'], unique=False)
    op.create_index(op.f('ix_consent_history_user_id'), 'consent_history', ['user_id'], unique=False)
    op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)
    
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=20), nullable=False),
    sa.Column('purpose', sa.String(length=50), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_audit_user_timestamp', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index('idx_user_purpose', table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_user_id'), table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_purpose'), table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_id'), table_name='consent_history')
    op.drop_table('consent_history')

