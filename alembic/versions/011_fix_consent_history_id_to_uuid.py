"""fix consent_history id to uuid

Revision ID: 011
Revises: 010
Create Date: 2025-12-01 07:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from sqlalchemy.exc import InternalError, OperationalError

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy.exc import InternalError, OperationalError
    
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
            if "current transaction is aborted" in str(e).lower():
                raise
            return False
        except Exception:
            return False
    
    # If id column doesn't exist, create it as UUID
    if not column_exists('consent_history', 'id'):
        try:
            # Check if table exists first
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'consent_history'
                )
            """))
            if table_check.scalar():
                # Table exists but id column doesn't - create it as nullable first
                op.add_column('consent_history', 
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=True)
                )
                # Set default values for existing rows if any
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
        return
    
    try:
        result = conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'consent_history' AND column_name = 'id'
        """))
    except (InternalError, OperationalError) as e:
        raise
    
    row = result.fetchone()
    if row and row[0]:
        current_type = row[0].lower()
        
        if 'uuid' in current_type:
            return
        
        if 'int' in current_type or current_type == 'integer':
            if column_exists('consent_history', 'id_new'):
                try:
                    op.alter_column('consent_history', 'id_new', nullable=False)
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
                
                if column_exists('consent_history', 'id'):
                    try:
                        op.drop_column('consent_history', 'id')
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass
                
                if not column_exists('consent_history', 'id') and column_exists('consent_history', 'id_new'):
                    try:
                        op.rename_column('consent_history', 'id_new', 'id')
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass
                
                if not constraint_exists('consent_history_pkey', 'consent_history') and column_exists('consent_history', 'id'):
                    try:
                        op.create_primary_key('consent_history_pkey', 'consent_history', ['id'])
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass
                return
            
            try:
                conn.execute(text("ALTER TABLE consent_history ALTER COLUMN id DROP DEFAULT"))
            except (InternalError, OperationalError) as e:
                raise
            except Exception as e:
                error_str = str(e).lower()
                if "no default" in error_str or "does not have a default" in error_str:
                    pass
                else:
                    raise
            
            if constraint_exists('consent_history_pkey', 'consent_history'):
                try:
                    op.drop_constraint('consent_history_pkey', 'consent_history', type_='primary')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
            
            indexes_to_drop = ['idx_user_purpose', 'idx_user_timestamp']
            for idx_name in indexes_to_drop:
                if index_exists(idx_name, 'consent_history'):
                    try:
                        op.drop_index(idx_name, table_name='consent_history')
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass
            
            if not column_exists('consent_history', 'id_new'):
                try:
                    op.add_column('consent_history', 
                        sa.Column('id_new', postgresql.UUID(as_uuid=True), nullable=True)
                    )
                except (InternalError, OperationalError) as e:
                    raise
                except Exception as e:
                    error_str = str(e).lower()
                    if "already exists" in error_str or "duplicate" in error_str:
                        pass
                    else:
                        raise
            
            if column_exists('consent_history', 'id_new'):
                try:
                    conn.execute(text("""
                        UPDATE consent_history 
                        SET id_new = gen_random_uuid()
                        WHERE id_new IS NULL
                    """))
                except (InternalError, OperationalError) as e:
                    raise
                except Exception as e:
                    error_str = str(e).lower()
                    if "violates" in error_str or "constraint" in error_str:
                        raise
                    pass
            
            if column_exists('consent_history', 'id_new'):
                try:
                    result = conn.execute(text("""
                        SELECT is_nullable 
                        FROM information_schema.columns 
                        WHERE table_name = 'consent_history' AND column_name = 'id_new'
                    """))
                    row = result.fetchone()
                    if row and row[0] == 'YES':
                        try:
                            op.alter_column('consent_history', 'id_new', nullable=False)
                        except (InternalError, OperationalError) as e:
                            if "current transaction is aborted" in str(e).lower():
                                raise
                        except Exception:
                            pass
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
            
            if column_exists('consent_history', 'id') and column_exists('consent_history', 'id_new'):
                try:
                    op.drop_column('consent_history', 'id')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
            
            if column_exists('consent_history', 'id_new') and not column_exists('consent_history', 'id'):
                try:
                    op.rename_column('consent_history', 'id_new', 'id')
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
            
            if not constraint_exists('consent_history_pkey', 'consent_history') and column_exists('consent_history', 'id'):
                try:
                    op.create_primary_key('consent_history_pkey', 'consent_history', ['id'])
                except (InternalError, OperationalError) as e:
                    if "current transaction is aborted" in str(e).lower():
                        raise
                except Exception:
                    pass
            
            if not index_exists('idx_user_purpose', 'consent_history'):
                if column_exists('consent_history', 'user_id') and column_exists('consent_history', 'purpose'):
                    try:
                        op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass
            
            if not index_exists('idx_user_timestamp', 'consent_history'):
                if column_exists('consent_history', 'user_id') and column_exists('consent_history', 'timestamp'):
                    try:
                        op.create_index('idx_user_timestamp', 'consent_history', ['user_id', 'timestamp'], unique=False)
                    except (InternalError, OperationalError) as e:
                        if "current transaction is aborted" in str(e).lower():
                            raise
                    except Exception:
                        pass


def downgrade() -> None:
    conn = op.get_bind()
    
    result = conn.execute(text("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_name = 'consent_history' AND column_name = 'id'
    """))
    
    row = result.fetchone()
    if row and row[0] and 'uuid' in row[0].lower():
        try:
            op.drop_constraint('consent_history_pkey', 'consent_history', type_='primary')
        except:
            pass
        
        try:
            op.drop_index('idx_user_purpose', table_name='consent_history')
        except:
            pass
        try:
            op.drop_index('idx_user_timestamp', table_name='consent_history')
        except:
            pass
        
        op.add_column('consent_history',
            sa.Column('id_int', sa.Integer(), nullable=False, autoincrement=True)
        )
        
        conn.execute(text("""
            UPDATE consent_history 
            SET id_int = row_number() OVER (ORDER BY timestamp)
        """))
        
        op.drop_column('consent_history', 'id')
        op.rename_column('consent_history', 'id_int', 'id')
        
        op.create_primary_key('consent_history_pkey', 'consent_history', ['id'])
        
        op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)
        op.create_index('idx_user_timestamp', 'consent_history', ['user_id', 'timestamp'], unique=False)
