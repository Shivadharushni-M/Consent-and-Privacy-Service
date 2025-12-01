"""Fix audit_logs table - ensure id column exists as UUID"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InternalError, OperationalError
from app.config import settings

engine = create_engine(settings.DATABASE_URL)
conn = engine.connect()

try:
    # Check current state
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'audit_logs' AND column_name IN ('id', 'id_new')
    """))
    
    columns = {row[0]: row[1] for row in result}
    
    print("Current state:")
    print(f"  Has 'id' column: {'id' in columns}")
    print(f"  Has 'id_new' column: {'id_new' in columns}")
    
    if 'id' in columns:
        print(f"  'id' column type: {columns['id']}")
        if 'uuid' in columns['id'].lower():
            print("✓ 'id' column exists and is UUID - no fix needed!")
            exit(0)
    
    # If id_new exists but id doesn't, rename it
    if 'id_new' in columns and 'id' not in columns:
        print("\nRenaming 'id_new' to 'id'...")
        conn.execute(text("ALTER TABLE audit_logs RENAME COLUMN id_new TO id"))
        print("✓ Renamed 'id_new' to 'id'")
        
        # Ensure primary key exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'audit_logs' 
                AND constraint_name = 'audit_logs_pkey'
            )
        """))
        if not result.scalar():
            print("Creating primary key...")
            conn.execute(text("ALTER TABLE audit_logs ADD PRIMARY KEY (id)"))
            print("✓ Created primary key")
        
        conn.commit()
        print("\n✓ Fix completed successfully!")
        
    elif 'id' not in columns and 'id_new' not in columns:
        # Neither exists - create id column
        print("\nCreating 'id' column as UUID...")
        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN id UUID NOT NULL DEFAULT gen_random_uuid()"))
        
        # Set primary key
        print("Setting primary key...")
        conn.execute(text("ALTER TABLE audit_logs ADD PRIMARY KEY (id)"))
        
        conn.commit()
        print("\n✓ Created 'id' column and primary key!")
        
    else:
        print("\n⚠ Unexpected state - manual intervention may be needed")
        
except Exception as e:
    conn.rollback()
    print(f"\n✗ Error: {e}")
    raise
finally:
    conn.close()
    engine.dispose()
