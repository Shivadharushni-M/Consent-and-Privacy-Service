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
    from sqlalchemy import text
    from sqlalchemy.exc import InternalError, OperationalError
    
    conn = op.get_bind()
    
    # Helper function to check if trigger exists
    def trigger_exists(trigger_name: str, table_name: str) -> bool:
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    WHERE t.tgname = :trigger_name
                    AND c.relname = :table_name
                )
            """), {"trigger_name": trigger_name, "table_name": table_name})
            return result.scalar() or False
        except (InternalError, OperationalError) as e:
            # If transaction is aborted, return False to be safe
            if "current transaction is aborted" in str(e).lower():
                return False
            raise
        except Exception:
            return False
    
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
    
    # Create trigger to prevent UPDATE (only if it doesn't exist)
    if not trigger_exists("audit_logs_prevent_update", "audit_logs"):
        op.execute("""
            CREATE TRIGGER audit_logs_prevent_update
            BEFORE UPDATE ON audit_logs
            FOR EACH ROW
            EXECUTE FUNCTION prevent_audit_log_update();
        """)
    
    # Create trigger to prevent DELETE (only if it doesn't exist)
    if not trigger_exists("audit_logs_prevent_delete", "audit_logs"):
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
