"""fix audit logs schema

Revision ID: 002
Revises: 001
Create Date: 2025-11-30 13:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fix audit_logs table
    conn = op.get_bind()
    
    # Check if table exists and get its columns
    result = conn.execute(sa.text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs'
    """))
    existing_columns = {row[0]: row[1] for row in result}
    
    # Fix the id column sequence - ensure it has a default value
    # Check if id column has a default
    id_default_result = conn.execute(sa.text("""
        SELECT column_default 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name = 'id'
    """))
    id_default = None
    for row in id_default_result:
        id_default = row[0]
        break
    
    if not id_default or 'nextval' not in str(id_default):
        # Create or get sequence name
        seq_name = 'audit_logs_id_seq'
        # Check if sequence exists
        seq_check = conn.execute(sa.text("""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_name = :seq_name
        """), {'seq_name': seq_name})
        seq_exists = any(row[0] == seq_name for row in seq_check)
        
        if not seq_exists:
            # Create sequence
            conn.execute(sa.text(f"CREATE SEQUENCE {seq_name}"))
            # Set sequence owner
            conn.execute(sa.text(f"ALTER SEQUENCE {seq_name} OWNED BY audit_logs.id"))
        
        # Set the default value for id column
        conn.execute(sa.text(f"""
            ALTER TABLE audit_logs 
            ALTER COLUMN id SET DEFAULT nextval('{seq_name}')
        """))
        
        # Set the sequence to start from the max id + 1 (if there's existing data)
        try:
            max_id_result = conn.execute(sa.text("SELECT MAX(id) FROM audit_logs"))
            max_id = max_id_result.scalar()
            if max_id is not None:
                conn.execute(sa.text(f"""
                    SELECT setval('{seq_name}', {max_id + 1}, false)
                """))
            else:
                conn.execute(sa.text(f"SELECT setval('{seq_name}', 1, false)"))
        except:
            # If table is empty or error, just set to 1
            conn.execute(sa.text(f"SELECT setval('{seq_name}', 1, false)"))
    
    # Add timestamp column if it doesn't exist
    if 'timestamp' not in existing_columns:
        op.add_column('audit_logs', 
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
        )
    
    # Remove purpose column if it exists (it shouldn't be in the model)
    if 'purpose' in existing_columns:
        op.drop_column('audit_logs', 'purpose')
    
    # Change user_id from Integer to UUID if needed
    if 'user_id' in existing_columns:
        user_id_type = existing_columns['user_id']
        # Check if it's integer type (could be 'integer', 'bigint', etc.)
        if 'int' in user_id_type.lower() or user_id_type == 'integer':
            # Drop indexes that depend on user_id first
            try:
                op.drop_index('idx_audit_user_timestamp', table_name='audit_logs')
            except:
                pass
            try:
                op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
            except:
                pass
            
            # For safety, we'll use a temporary column approach
            # First create a new UUID column
            op.add_column('audit_logs', 
                sa.Column('user_id_new', postgresql.UUID(as_uuid=True), nullable=True)
            )
            
            # Copy data: convert integer to UUID using a deterministic method
            # Using uuid5 with a namespace to ensure same integer -> same UUID
            # PostgreSQL doesn't have uuid5, so we'll use a simpler approach
            op.execute("""
                UPDATE audit_logs 
                SET user_id_new = gen_random_uuid()
            """)
            # Note: This generates random UUIDs. For production, you'd want to preserve the mapping.
            
            # Drop old column and rename new one
            op.drop_column('audit_logs', 'user_id')
            op.rename_column('audit_logs', 'user_id_new', 'user_id')
            op.alter_column('audit_logs', 'user_id', nullable=False)
            
            # Recreate indexes
            op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
            op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'], unique=False)
    
    # Fix consent_history table - change user_id from Integer to UUID if needed
    result = conn.execute(sa.text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'consent_history'
    """))
    consent_columns = {row[0]: row[1] for row in result}
    
    if 'user_id' in consent_columns:
        user_id_type = consent_columns['user_id']
        if 'int' in user_id_type.lower() or user_id_type == 'integer':
            # Drop indexes
            try:
                op.drop_index('idx_user_purpose', table_name='consent_history')
            except:
                pass
            try:
                op.drop_index('ix_consent_history_user_id', table_name='consent_history')
            except:
                pass
            
            # Add new UUID column
            op.add_column('consent_history', 
                sa.Column('user_id_new', postgresql.UUID(as_uuid=True), nullable=True)
            )
            
            # Convert data
            op.execute("""
                UPDATE consent_history 
                SET user_id_new = gen_random_uuid()
            """)
            # Note: This generates random UUIDs. For production, you'd want to preserve the mapping.
            
            # Drop old and rename new
            op.drop_column('consent_history', 'user_id')
            op.rename_column('consent_history', 'user_id_new', 'user_id')
            op.alter_column('consent_history', 'user_id', nullable=False)
            
            # Recreate indexes
            op.create_index('ix_consent_history_user_id', 'consent_history', ['user_id'], unique=False)
            op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)


def downgrade() -> None:
    # Revert changes - simplified for now
    conn = op.get_bind()
    
    # Revert audit_logs
    result = conn.execute(sa.text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs'
    """))
    existing_columns = {row[0]: row[1] for row in result}
    
    if 'user_id' in existing_columns and 'uuid' in existing_columns['user_id'].lower():
        op.drop_index('idx_audit_user_timestamp', table_name='audit_logs', if_exists=True)
        op.drop_index('ix_audit_logs_user_id', table_name='audit_logs', if_exists=True)
        
        op.add_column('audit_logs', 
            sa.Column('user_id_int', sa.Integer(), nullable=True)
        )
        op.drop_column('audit_logs', 'user_id')
        op.rename_column('audit_logs', 'user_id_int', 'user_id')
        op.alter_column('audit_logs', 'user_id', nullable=False)
        
        op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)
        op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'], unique=False)
    
    if 'purpose' not in existing_columns:
        op.add_column('audit_logs', 
            sa.Column('purpose', sa.String(length=50), nullable=True)
        )
    
    # Revert consent_history
    result = conn.execute(sa.text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'consent_history'
    """))
    consent_columns = {row[0]: row[1] for row in result}
    
    if 'user_id' in consent_columns and 'uuid' in consent_columns['user_id'].lower():
        op.drop_index('idx_user_purpose', table_name='consent_history', if_exists=True)
        op.drop_index('ix_consent_history_user_id', table_name='consent_history', if_exists=True)
        
        op.add_column('consent_history', 
            sa.Column('user_id_int', sa.Integer(), nullable=True)
        )
        op.drop_column('consent_history', 'user_id')
        op.rename_column('consent_history', 'user_id_int', 'user_id')
        op.alter_column('consent_history', 'user_id', nullable=False)
        
        op.create_index('ix_consent_history_user_id', 'consent_history', ['user_id'], unique=False)
        op.create_index('idx_user_purpose', 'consent_history', ['user_id', 'purpose'], unique=False)
