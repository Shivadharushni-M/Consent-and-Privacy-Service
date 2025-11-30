#!/usr/bin/env python3
from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    trans = conn.begin()
    try:
        # Add missing enum values
        print("Adding missing enum values...")
        conn.execute(text("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'ads'"))
        conn.execute(text("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'email'"))
        conn.execute(text("ALTER TYPE purpose_enum ADD VALUE IF NOT EXISTS 'location'"))
        trans.commit()
        print('✓ Successfully added missing enum values')
    except Exception as e:
        trans.rollback()
        print(f'✗ Error: {e}')
