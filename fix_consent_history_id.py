"""One-time script to fix consent_history id column issue"""
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InternalError, OperationalError
from app.config import settings

def fix_consent_history_id():
    """Fix the consent_history id column issue"""
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Check if id_new exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'consent_history' AND column_name = 'id_new'
            """))
            id_new_exists = result.fetchone() is not None
            
            # Check if id exists and its type
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'consent_history' AND column_name = 'id'
            """))
            id_row = result.fetchone()
            id_exists = id_row is not None
            id_is_uuid = False
            if id_exists:
                id_is_uuid = 'uuid' in id_row[1].lower() if id_row[1] else False
            
            print(f"Current state: id_new exists={id_new_exists}, id exists={id_exists}, id is UUID={id_is_uuid}")
            
            if id_new_exists:
                # Check if id_new is nullable
                result = conn.execute(text("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'consent_history' AND column_name = 'id_new'
                """))
                row = result.fetchone()
                is_nullable = row[0] == 'YES' if row else True
                
                print(f"id_new is nullable: {is_nullable}")
                
                # If NOT NULL, temporarily make it nullable
                if not is_nullable:
                    print("Making id_new nullable temporarily...")
                    conn.execute(text("ALTER TABLE consent_history ALTER COLUMN id_new DROP NOT NULL"))
                    conn.commit()
                    trans = conn.begin()  # Start new transaction
                
                # Populate NULL values
                print("Populating NULL values in id_new...")
                conn.execute(text("""
                    UPDATE consent_history 
                    SET id_new = gen_random_uuid()
                    WHERE id_new IS NULL
                """))
                
                # Make it NOT NULL
                print("Making id_new NOT NULL...")
                conn.execute(text("ALTER TABLE consent_history ALTER COLUMN id_new SET NOT NULL"))
                
                # If id doesn't exist or is not UUID, complete the migration
                if not id_exists or not id_is_uuid:
                    if id_exists and not id_is_uuid:
                        print("Dropping old integer id column...")
                        # Drop primary key constraint first
                        try:
                            conn.execute(text("ALTER TABLE consent_history DROP CONSTRAINT IF EXISTS consent_history_pkey"))
                        except Exception:
                            pass
                        # Drop the old id column
                        conn.execute(text("ALTER TABLE consent_history DROP COLUMN IF EXISTS id"))
                    
                    # Rename id_new to id
                    print("Renaming id_new to id...")
                    conn.execute(text("ALTER TABLE consent_history RENAME COLUMN id_new TO id"))
                    
                    # Create primary key
                    print("Creating primary key constraint...")
                    conn.execute(text("ALTER TABLE consent_history ADD PRIMARY KEY (id)"))
                else:
                    # id already exists and is UUID, just drop id_new
                    print("id column already exists as UUID, dropping id_new...")
                    conn.execute(text("ALTER TABLE consent_history DROP COLUMN IF EXISTS id_new"))
                
                trans.commit()
                print("✓ Fix completed successfully!")
            else:
                print("id_new column doesn't exist. Migration may have already completed.")
                trans.commit()
                
        except Exception as e:
            trans.rollback()
            print(f"✗ Error: {e}")
            raise

if __name__ == "__main__":
    fix_consent_history_id()
