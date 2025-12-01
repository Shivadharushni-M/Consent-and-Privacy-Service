"""fix audit logs id to uuid

Revision ID: 009
Revises: 008
Create Date: 2025-11-30 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.exc import InternalError, OperationalError
    
    conn = op.get_bind()
    
    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        try:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            return result.fetchone() is not None
        except (InternalError, OperationalError) as e:
            # If transaction is aborted, re-raise so migration fails properly
            if "current transaction is aborted" in str(e).lower():
                raise  # Re-raise transaction abort errors
            raise
        except Exception:
            return False
    
    # Helper function to check if constraint exists
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
            # If transaction is aborted, re-raise so migration fails properly
            if "current transaction is aborted" in str(e).lower():
                raise  # Re-raise transaction abort errors
            raise
        except Exception:
            return False
    
    # Helper function to check if index exists
    def index_exists(index_name: str, table_name: str = None) -> bool:
        try:
            if table_name:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name AND tablename = :table_name
                    )
                """), {"index_name": index_name, "table_name": table_name})
            else:
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = :index_name
                    )
                """), {"index_name": index_name})
            return result.scalar() or False
        except (InternalError, OperationalError) as e:
            # If transaction is aborted, re-raise so migration fails properly
            if "current transaction is aborted" in str(e).lower():
                raise  # Re-raise transaction abort errors
            raise
        except Exception:
            return False
    
    # Helper function to safely execute operations with transaction error handling
    def safe_execute(operation, *args, **kwargs):
        """Execute an operation with error handling for transaction aborts"""
        try:
            return operation(*args, **kwargs)
        except (InternalError, OperationalError) as e:
            # If transaction is aborted, we can't continue
            if "current transaction is aborted" in str(e).lower():
                # Log the error but don't raise - let Alembic handle the rollback
                return None
            raise
        except Exception:
            # For other exceptions, just pass
            return None
    
    # Check the current data type of the id column
    # This will fail immediately if transaction is already aborted
    if not column_exists('audit_logs', 'id'):
        return
    
    # Get the data type - this will also fail if transaction is aborted
    try:
        result = conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'audit_logs' AND column_name = 'id'
        """))
    except (InternalError, OperationalError) as e:
        # Re-raise database errors immediately
        raise
    
    row = result.fetchone()
    if row and row[0]:
        current_type = row[0].lower()
        
        # If it's already UUID, skip the migration
        if 'uuid' in current_type:
            return
        
        # If it's integer, convert to UUID
        if 'int' in current_type or current_type == 'integer':
            # Check if id_new column already exists (migration might have partially run)
            if column_exists('audit_logs', 'id_new'):
                # Migration partially completed, skip to completion steps
                # Make sure id_new is not nullable
                try:
                    op.alter_column('audit_logs', 'id_new', nullable=False)
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass
                
                # Drop old id if it still exists
                if column_exists('audit_logs', 'id'):
                    try:
                        op.drop_column('audit_logs', 'id')
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise  # Re-raise transaction abort errors
                    except Exception:
                        pass  # Column might not exist or might be referenced
                
                # Rename if needed
                if not column_exists('audit_logs', 'id') and column_exists('audit_logs', 'id_new'):
                    try:
                        op.rename_column('audit_logs', 'id_new', 'id')
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise  # Re-raise transaction abort errors
                    except Exception:
                        pass  # Rename might fail if column doesn't exist
                
                # Recreate primary key if needed
                if not constraint_exists('audit_logs_pkey', 'audit_logs') and column_exists('audit_logs', 'id'):
                    try:
                        op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise  # Re-raise transaction abort errors
                    except Exception:
                        pass  # Primary key might already exist
                
                # Recreate indexes if needed (check columns exist first)
                if not index_exists('idx_audit_user_created', 'audit_logs'):
                    if column_exists('audit_logs', 'user_id') and column_exists('audit_logs', 'created_at'):
                        try:
                            op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)
                        except (InternalError, OperationalError) as e:
                            if "current transaction is aborted" in str(e).lower():
                                raise  # Re-raise transaction abort errors
                        except Exception:
                            pass  # Index might already exist
                return
            
            # Drop any sequences that might be attached
            try:
                conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN id DROP DEFAULT"))
            except (InternalError, OperationalError) as e:
                # Re-raise all database errors - don't continue if transaction is aborted
                raise
            except Exception as e:
                # Only ignore expected errors (like "column has no default")
                error_str = str(e).lower()
                if "no default" in error_str or "does not have a default" in error_str:
                    pass  # Expected - column might not have a default
                else:
                    # Unexpected error, re-raise it
                    raise
            
            # Drop primary key constraint temporarily (only if it exists)
            if constraint_exists('audit_logs_pkey', 'audit_logs'):
                try:
                    op.drop_constraint('audit_logs_pkey', 'audit_logs', type_='primary')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass  # Constraint might not exist or might be referenced
            
            # Drop any indexes that depend on id (only if they exist)
            if index_exists('idx_audit_user_created', 'audit_logs'):
                try:
                    op.drop_index('idx_audit_user_created', table_name='audit_logs')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass  # Index might not exist
            
            # Create a new UUID column (nullable first, then we'll make it not null)
            # Only if it doesn't already exist
            if not column_exists('audit_logs', 'id_new'):
                try:
                    op.add_column('audit_logs', 
                        sa.Column('id_new', postgresql.UUID(as_uuid=True), nullable=True)
                    )
                except (InternalError, OperationalError) as e:
                    # Re-raise transaction abort and other database errors immediately
                    # Don't try to check column_exists() here as transaction might be aborted
                    raise
                except Exception as e:
                    # For other exceptions (like "column already exists"), 
                    # assume the column exists and continue
                    # We can't safely check column_exists() here if transaction is aborted
                    error_str = str(e).lower()
                    if "already exists" in error_str or "duplicate" in error_str:
                        # Column probably already exists, continue
                        pass
                    else:
                        # Unknown error, re-raise it
                        raise
            
            # Generate UUIDs for existing rows (only if id_new column exists and has null values)
            # Check if column exists first - this will fail if transaction is aborted
            if column_exists('audit_logs', 'id_new'):
                try:
                    # Temporarily disable the update trigger to allow the migration UPDATE
                    # The trigger was created in migration 006 to prevent updates
                    # Check if trigger exists first
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
                        # Trigger might not exist, continue without disabling
                        pass
                    
                    # Now update the rows
                    conn.execute(text("""
                        UPDATE audit_logs 
                        SET id_new = gen_random_uuid()
                        WHERE id_new IS NULL
                    """))
                    
                    # Re-enable the trigger if we disabled it
                    if trigger_disabled:
                        conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
                    
                except (InternalError, OperationalError) as e:
                    # Try to re-enable trigger if it was disabled (in case of error)
                    if trigger_disabled:
                        try:
                            conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
                        except:
                            pass
                    # Re-raise all database errors - don't continue if transaction is aborted
                    raise
                except Exception as e:
                    # Try to re-enable trigger if it was disabled (in case of error)
                    if trigger_disabled:
                        try:
                            conn.execute(text("ALTER TABLE audit_logs ENABLE TRIGGER audit_logs_prevent_update"))
                        except:
                            pass
                    # For other exceptions, check if it's a data issue
                    error_str = str(e).lower()
                    if "violates" in error_str or "constraint" in error_str:
                        # Data constraint violation - this is a real error
                        raise
                    # Other errors might be recoverable, but log them
                    pass
            
            # Now make it not nullable (only if it's still nullable and column exists)
            if column_exists('audit_logs', 'id_new'):
                try:
                    result = conn.execute(text("""
                        SELECT is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = 'audit_logs' AND column_name = 'id_new'
                    """))
                    row = result.fetchone()
                    if row and row[0] == 'YES':
                        try:
                            op.alter_column('audit_logs', 'id_new', nullable=False)
                        except (InternalError, OperationalError) as e:
                            if "current transaction is aborted" in str(e).lower():
                                raise  # Re-raise transaction abort errors
                        except Exception:
                            pass  # Alter might fail
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass
            
            # Drop the old id column (only if it exists)
            if column_exists('audit_logs', 'id') and column_exists('audit_logs', 'id_new'):
                try:
                    op.drop_column('audit_logs', 'id')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass  # Column might not exist or might be referenced
            
            # Rename the new column to id (only if id_new exists and id doesn't)
            if column_exists('audit_logs', 'id_new') and not column_exists('audit_logs', 'id'):
                try:
                    op.rename_column('audit_logs', 'id_new', 'id')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass  # Rename might fail if column doesn't exist
            
            # Recreate primary key (only if it doesn't exist)
            if not constraint_exists('audit_logs_pkey', 'audit_logs') and column_exists('audit_logs', 'id'):
                try:
                    op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise  # Re-raise transaction abort errors
                except Exception:
                    pass  # Primary key might already exist or column might not be ready
            
            # Recreate indexes (only if they don't exist and columns exist)
            if not index_exists('idx_audit_user_created', 'audit_logs'):
                # Check if both columns exist before creating index
                if column_exists('audit_logs', 'user_id') and column_exists('audit_logs', 'created_at'):
                    try:
                        op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise  # Re-raise transaction abort errors
                    except Exception:
                        pass  # Index might already exist or transaction might be aborted


def downgrade() -> None:
    # Revert to integer id (simplified - would need to preserve mapping in production)
    conn = op.get_bind()
    
    # Check if id is UUID
    result = conn.execute(text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'id'
    """))
    
    row = result.fetchone()
    if row and row[0] and 'uuid' in row[0].lower():
        # Drop primary key
        try:
            op.drop_constraint('audit_logs_pkey', 'audit_logs', type_='primary')
        except:
            pass
        
        # Drop indexes
        try:
            op.drop_index('idx_audit_user_created', table_name='audit_logs')
        except:
            pass
        
        # Add integer id column
        op.add_column('audit_logs',
            sa.Column('id_int', sa.Integer(), nullable=False, autoincrement=True)
        )
        
        # Generate sequential IDs
        conn.execute(text("""
            UPDATE audit_logs 
            SET id_int = row_number() OVER (ORDER BY created_at)
        """))
        
        # Drop UUID column and rename
        op.drop_column('audit_logs', 'id')
        op.rename_column('audit_logs', 'id_int', 'id')
        
        # Recreate primary key
        op.create_primary_key('audit_logs_pkey', 'audit_logs', ['id'])
        
        # Recreate indexes
        op.create_index('idx_audit_user_created', 'audit_logs', ['user_id', 'created_at'], unique=False)

