"""add audit log immutability constraints

Revision ID: 006
Revises: 005
Create Date: 2025-01-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create a function to prevent UPDATE on audit_logs
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable. UPDATE operations are not allowed on audit_logs table.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create a function to prevent DELETE on audit_logs
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable. DELETE operations are not allowed on audit_logs table.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger to prevent UPDATE
    op.execute("""
        CREATE TRIGGER audit_logs_prevent_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_update();
    """)
    
    # Create trigger to prevent DELETE
    op.execute("""
        CREATE TRIGGER audit_logs_prevent_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_delete();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS audit_logs_prevent_update ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_prevent_delete ON audit_logs;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_update();")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_delete();")
