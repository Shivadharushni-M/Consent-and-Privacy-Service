#!/usr/bin/env python3
"""Direct database check"""
from sqlalchemy import text
from app.db.database import engine

with engine.connect() as conn:
    # Check in public schema explicitly
    result = conn.execute(text("""
        SELECT n.nspname as schema, t.typname as enum_name
        FROM pg_type t 
        JOIN pg_namespace n ON n.oid = t.typnamespace 
        WHERE t.typtype = 'e' AND n.nspname = 'public'
    """))
    enums = list(result)
    print(f"Enums in public schema: {enums}")
    
    # Try to drop region_enum specifically
    if any('region_enum' in str(e) for e in enums):
        print("\nAttempting to drop region_enum...")
        try:
            with engine.begin() as trans_conn:
                trans_conn.execute(text('DROP TYPE IF EXISTS region_enum CASCADE'))
            print("Dropped region_enum successfully")
        except Exception as e:
            print(f"Error: {e}")

