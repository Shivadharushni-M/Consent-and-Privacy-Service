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

purpose_enum = sa.Enum(
    'analytics',
    'marketing',
    'personalization',
    'data_sharing',
    name='purpose_enum'
)
status_enum = sa.Enum('granted', 'denied', 'revoked', name='status_enum')
region_enum = sa.Enum(
    'EU',
    'US',
    'IN',
    'BR',
    'SG',
    'AU',
    'JP',
    'CA',
    'UK',
    'ZA',
    'KR',
    name='region_enum'
)
retention_entity_enum = sa.Enum('consent', 'audit', 'user', name='retention_entity_enum')
request_type_enum = sa.Enum('access', 'delete', 'export', 'rectify', name='request_type_enum')
request_status_enum = sa.Enum('pending', 'completed', 'failed', name='request_status_enum')


def upgrade() -> None:
    bind = op.get_bind()
    purpose_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)
    region_enum.create(bind, checkfirst=True)
    retention_entity_enum.create(bind, checkfirst=True)
    request_type_enum.create(bind, checkfirst=True)
    request_status_enum.create(bind, checkfirst=True)

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('region', region_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    op.create_table(
        'consent_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('purpose', purpose_enum, nullable=False),
        sa.Column('status', status_enum, nullable=False),
        sa.Column('region', region_enum, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consent_history_user_id'), 'consent_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_consent_history_purpose'), 'consent_history', ['purpose'], unique=False)
    op.create_index(op.f('ix_consent_history_timestamp'), 'consent_history', ['timestamp'], unique=False)
    op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)
    op.create_index('idx_user_timestamp', 'consent_history', ['user_id', 'timestamp'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)

    op.create_table(
        'retention_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', retention_entity_enum, nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_retention_schedules_entity_type'), 'retention_schedules', ['entity_type'], unique=True)

    op.create_table(
        'subject_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_type', request_type_enum, nullable=False),
        sa.Column('status', request_status_enum, nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subject_requests_user_id'), 'subject_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_subject_requests_request_type'), 'subject_requests', ['request_type'], unique=False)
    op.create_index(op.f('ix_subject_requests_status'), 'subject_requests', ['status'], unique=False)
    op.create_index('idx_user_request_type', 'subject_requests', ['user_id', 'request_type'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_user_request_type', table_name='subject_requests')
    op.drop_index(op.f('ix_subject_requests_status'), table_name='subject_requests')
    op.drop_index(op.f('ix_subject_requests_request_type'), table_name='subject_requests')
    op.drop_index(op.f('ix_subject_requests_user_id'), table_name='subject_requests')
    op.drop_table('subject_requests')

    op.drop_index(op.f('ix_retention_schedules_entity_type'), table_name='retention_schedules')
    op.drop_table('retention_schedules')

    op.drop_index('idx_audit_user_created', table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index('idx_user_timestamp', table_name='consent_history')
    op.drop_index('idx_user_purpose', table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_timestamp'), table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_purpose'), table_name='consent_history')
    op.drop_index(op.f('ix_consent_history_user_id'), table_name='consent_history')
    op.drop_table('consent_history')

    op.drop_table('users')

    bind = op.get_bind()
    request_status_enum.drop(bind, checkfirst=True)
    request_type_enum.drop(bind, checkfirst=True)
    retention_entity_enum.drop(bind, checkfirst=True)
    region_enum.drop(bind, checkfirst=True)
    status_enum.drop(bind, checkfirst=True)
    purpose_enum.drop(bind, checkfirst=True)
