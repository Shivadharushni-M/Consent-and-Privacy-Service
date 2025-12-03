#!/usr/bin/env python
"""Fix Alembic version table if it contains invalid revision '012'."""
import sys
from sqlalchemy import create_engine, text
from app.config import settings

def fix_alembic_version():
    """Update alembic_version table if it contains invalid revision."""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.begin() as conn:
            # Check if alembic_version table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                print("ℹ️  alembic_version table doesn't exist yet (first migration)")
                return False
            
            # Check current revision
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.scalar()
            
            # If it's the invalid '012', fix it
            if current == '012':
                print(f"⚠️  Found invalid revision '012', updating to '008'...")
                conn.execute(text("UPDATE alembic_version SET version_num = '008'"))
                print("✅ Fixed alembic_version table")
                return True
            else:
                print(f"✅ Database revision '{current}' is valid")
                return False
                
    except Exception as e:
        print(f"⚠️  Could not check/fix alembic_version: {e}")
        # Don't fail the build if we can't connect
        return False

if __name__ == "__main__":
    fix_alembic_version()
