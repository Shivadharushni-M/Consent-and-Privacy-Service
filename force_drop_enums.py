#!/usr/bin/env python3
"""Force drop all enums"""
from sqlalchemy import text
from app.db.database import engine

enums = ['region_enum', 'purpose_enum', 'status_enum', 'retention_entity_enum', 
         'request_type_enum', 'request_status_enum', 'vendor_enum', 'event_name_enum']

with engine.begin() as conn:
    for enum_name in enums:
        try:
            conn.execute(text(f'DROP TYPE IF EXISTS {enum_name} CASCADE'))
            print(f"Dropped {enum_name}")
        except Exception as e:
            print(f"Error dropping {enum_name}: {e}")

print("Done. All enums dropped.")

