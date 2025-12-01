"""Direct script to fix audit_logs.id column type"""
from app.db.database import engine
from sqlalchemy import text

def apply_fix():
    with engine.begin() as conn:
        # Check current type
        result = conn.execute(text("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'audit_logs' AND column_name = 'id'
        """))
        row = result.fetchone()
        
        if not row:
            print("ERROR: audit_logs table or id column not found")
            return
        
        current_type = row[0].lower()
        print(f"Current audit_logs.id type: {current_type}")
        
        if 'uuid' in current_type:
            print("✓ Column is already UUID type. No fix needed.")
            return
        
        if 'int' in current_type or current_type == 'integer':
            print("Converting audit_logs.id from integer to UUID...")
            
            # Drop default if exists
            try:
                conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN id DROP DEFAULT"))
            except Exception as e:
                print(f"  (Could not drop default: {e})")
            
            # Drop primary key
            try:
                conn.execute(text("ALTER TABLE audit_logs DROP CONSTRAINT audit_logs_pkey"))
            except Exception as e:
                print(f"  (Could not drop PK: {e})")
            
            # Drop index if exists
            try:
                conn.execute(text("DROP INDEX IF EXISTS idx_audit_user_created"))
            except Exception as e:
                print(f"  (Could not drop index: {e})")
            
            # Create new UUID column
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN id_new UUID"))
            
            # Generate UUIDs for existing rows
            conn.execute(text("UPDATE audit_logs SET id_new = gen_random_uuid()"))
            
            # Make it not null
            conn.execute(text("ALTER TABLE audit_logs ALTER COLUMN id_new SET NOT NULL"))
            
            # Drop old column
            conn.execute(text("ALTER TABLE audit_logs DROP COLUMN id"))
            
            # Rename new column
            conn.execute(text("ALTER TABLE audit_logs RENAME COLUMN id_new TO id"))
            
            # Recreate primary key
            conn.execute(text("ALTER TABLE audit_logs ADD PRIMARY KEY (id)"))
            
            # Recreate index
            conn.execute(text("CREATE INDEX idx_audit_user_created ON audit_logs(user_id, created_at)"))
            
            print("✓ Successfully converted audit_logs.id to UUID type")
        else:
            print(f"⚠ Unexpected type: {current_type}")

if __name__ == "__main__":
    apply_fix()
