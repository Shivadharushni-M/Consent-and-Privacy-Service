#!/usr/bin/env python3
from app.db.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        # Try to cast 'location' to the enum
        result = conn.execute(text("SELECT 'location'::purpose_enum"))
        print('✓ location is valid in purpose_enum')
    except Exception as e:
        print(f'✗ location NOT in enum: {e}')
    
    # List all enum values
    try:
        result = conn.execute(text("SELECT unnest(enum_range(NULL::purpose_enum))"))
        values = [row[0] for row in result]
        print(f'Current enum values: {values}')
    except Exception as e:
        print(f'Error listing enum values: {e}')
