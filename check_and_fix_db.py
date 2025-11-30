#!/usr/bin/env python3
"""Script to check database state and fix enum issues"""
from sqlalchemy import text
from app.db.database import engine

def check_enums():
    """Check existing enums"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        enums = [r[0] for r in result]
        print(f"Existing enums: {enums}")
        return enums

def drop_enums():
    """Drop existing enums if they exist"""
    enums_to_drop = ['region_enum', 'purpose_enum', 'status_enum', 'retention_entity_enum', 
                     'request_type_enum', 'request_status_enum', 'vendor_enum', 'event_name_enum']
    
    with engine.begin() as conn:
        # First, check what actually exists
        result = conn.execute(text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
        existing = [r[0] for r in result]
        print(f"Found existing enums: {existing}")
        
        for enum_name in enums_to_drop:
            if enum_name in existing:
                try:
                    conn.execute(text(f'DROP TYPE IF EXISTS {enum_name} CASCADE'))
                    print(f"Dropped {enum_name}")
                except Exception as e:
                    print(f"Error dropping {enum_name}: {e}")
            else:
                print(f"{enum_name} does not exist, skipping")

if __name__ == "__main__":
    print("Checking database state...")
    existing = check_enums()
    
    if existing:
        print(f"\nFound {len(existing)} existing enums. Dropping them...")
        drop_enums()
        print("Enums dropped. You can now run migrations.")
    else:
        print("No existing enums found. Database is clean.")

