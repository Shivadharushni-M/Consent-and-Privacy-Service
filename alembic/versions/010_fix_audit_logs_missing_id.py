"""fix audit logs missing id column

Revision ID: 010
Revises: 009
Create Date: 2025-12-01 07:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from sqlalchemy.exc import InternalError, OperationalError

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix audit_logs table if id column is missing"""
    conn = op.get_bind()
    
    def column_exists(table_name: str, column_name: str) -> bool:
        try:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            return result.fetchone() is not None
        except (InternalError, OperationalError) as e:
            if "current transaction is aborted" in str(e).lower():
                raise
            return False
        except Exception:
            return False
    
    def constraint_exists(constraint_name: str, table_name: str) -> bool:
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = :constraint_name 
                    AND table_name = :table_name
                )
            """), {"constraint_name": constraint_name, "table_name": table_name})
            return result.scalar() or False
        except (InternalError, OperationalError) as e:
            if "current transaction is aborted" in str(e).lower():
                raise
            return False
        except Exception:
            return False
    
    has_id = column_exists('audit_logs', 'id')
    has_id_new = column_exists('audit_logs', 'id_new')
    
    if has_id:
        try:
            result = conn.execute(text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'audit_logs' AND column_name = 'id'
            """))
            row = result.fetchone()
            if row and 'uuid' in row[0].lower():
                return
        except (InternalError, OperationalError) as e:
            if "current transaction is aborted" in str(e).lower():
                raise
        except Exception:
            pass
    
    if has_id_new and not has_id:
        try:
            op.rename_column('audit_logs', 'id_new', 'id')
        except (InternalError, OperationalError) as e:
            if "current transaction is aborted" in str(e).lower():
                raise
        except Exception as e:
            error_str = str(e).lower()
            if "already exists" not in error_str and "does not exist" not in error_str:
                raise
        
        if not constraint_exists('audit_logs_pkey', 'audit_logs'):
            try:
                op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
            except (InternalError, OperationalError) as e:
                if "current transaction is aborted" in str(e).lower():
                    raise
            except Exception:
                pass
        return
    
    if not has_id and not has_id_new:
        trigger_disabled = False
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_trigger t
                    JOIN pg_class c ON t.tgrelid = c.oid
                    WHERE t.tgname = 'audit_logs_prevent_update'
                    AND c.relname = 'audit_logs'
                )
            """))
            if result.scalar():
                conn.execute(text("ALTER TABLE audit_logs DISABLE TRIGGER audit_logs_prevent_update"))
                trigger_disabled = True
        except Exception:
            pass
        
        try:
            op.add_column('audit_logs', 
                sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'))
            )
            if not constraint_exists('audit_logs_pkey', 'audit_logs'):
                op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
        except (InternalError, OperationalError) as e:
            if trigger_disabled:
                try:
                    conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
                except:
                    pass
            if "current transaction is aborted" in str(e).lower():
                raise
            raise
        except Exception as e:
            if trigger_disabled:
                try:
                    conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
                except:
                    pass
            error_str = str(e).lower()
            if "already exists" not in error_str:
                raise
        
        if trigger_disabled:
            try:
                conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
            except Exception:
                pass


def downgrade() -> None:
    pass
