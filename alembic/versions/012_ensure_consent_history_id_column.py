"""ensure consent_history id column

Revision ID: 012
Revises: 011
Create Date: 2025-12-01 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from sqlalchemy.exc import InternalError, OperationalError

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    
    def table_exists(table_name: str) -> bool:
        try:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """), {"table_name": table_name})
            return result.scalar() or False
        except (InternalError, OperationalError) as e:
            if "current transaction is aborted" in str(e).lower():
                raise
            return False
        except Exception:
            return False
    
    # Ensure consent_history table has id column
    if table_exists('consent_history'):
        # Check if id_new exists (incomplete migration 011)
        if column_exists('consent_history', 'id_new'):
            try:
                # Check if id_new is nullable
                is_nullable = True
                try:
                    result = conn.execute(text("""
                        SELECT is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = 'consent_history' AND column_name = 'id_new'
                    """))
                    row = result.fetchone()
                    if row:
                        is_nullable = row[0] == 'YES'
                except Exception:
                    pass
                
                # If id_new is NOT NULL, temporarily make it nullable to populate NULL values
                if not is_nullable:
                    try:
                        op.alter_column('consent_history', 'id_new', nullable=True)
                    except Exception:
                        pass
                
                # Populate id_new with UUIDs for any NULL values
                conn.execute(text("""
                    UPDATE consent_history 
                    SET id_new = gen_random_uuid()
                    WHERE id_new IS NULL
                """))
                
                # Make id_new non-nullable
                try:
                    op.alter_column('consent_history', 'id_new', nullable=False)
                except Exception:
                    pass
                
                # Check if id column exists and what type it is
                id_exists = column_exists('consent_history', 'id')
                id_is_uuid = False
                if id_exists:
                    try:
                        result = conn.execute(text("""
                            SELECT data_type 
                            FROM information_schema.columns 
                            WHERE table_name = 'consent_history' AND column_name = 'id'
                        """))
                        row = result.fetchone()
                        if row and row[0] and 'uuid' in row[0].lower():
                            id_is_uuid = True
                    except Exception:
                        pass
                
                # If id doesn't exist or is not UUID, complete the migration
                if not id_exists or not id_is_uuid:
                    # Drop old id column if it exists and is not UUID
                    if id_exists and not id_is_uuid:
                        # Drop primary key constraint first if it exists
                        if constraint_exists('consent_history_pkey', 'consent_history'):
                            try:
                                op.drop_constraint('consent_history_pkey', 'consent_history', type_='primary')
                            except Exception:
                                pass
                        # Drop the old id column
                        try:
                            op.drop_column('consent_history', 'id')
                        except Exception:
                            pass
                    
                    # Rename id_new to id
                    if not column_exists('consent_history', 'id'):
                        try:
                            op.rename_column('consent_history', 'id_new', 'id')
                        except Exception:
                            pass
                    
                    # Create primary key constraint if it doesn't exist
                    if not constraint_exists('consent_history_pkey', 'consent_history') and column_exists('consent_history', 'id'):
                        op.create_primary_key('consent_history_pkey', 'consent_history', ['id'])
                else:
                    # id already exists and is UUID - migration is complete, just drop id_new
                    try:
                        op.drop_column('consent_history', 'id_new')
                    except Exception:
                        pass
            except (InternalError, OperationalError) as e:
                raise
            except Exception as e:
                error_str = str(e).lower()
                if "already exists" in error_str or "duplicate" in error_str:
                    pass
                else:
                    raise
        
        # If id column doesn't exist and id_new doesn't exist either, create id
        elif not column_exists('consent_history', 'id'):
            try:
                # Add id column as nullable first
                op.add_column('consent_history', 
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=True)
                )
                
                # Set UUID values for existing rows
                conn.execute(text("""
                    UPDATE consent_history 
                    SET id = gen_random_uuid()
                    WHERE id IS NULL
                """))
                
                # Make it non-nullable
                op.alter_column('consent_history', 'id', nullable=False)
                
                # Create primary key constraint if it doesn't exist
                if not constraint_exists('consent_history_pkey', 'consent_history'):
                    op.create_primary_key('consent_history_pkey', 'consent_history', ['id'])
            except (InternalError, OperationalError) as e:
                raise
            except Exception as e:
                error_str = str(e).lower()
                if "already exists" in error_str or "duplicate" in error_str:
                    pass
                else:
                    raise


def downgrade() -> None:
    # No downgrade needed - we're just ensuring the column exists
    pass
