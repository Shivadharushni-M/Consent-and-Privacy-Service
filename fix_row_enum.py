"""Add ROW region to database enum"""
import psycopg2

try:
    conn = psycopg2.connect('postgresql://postgres:shiva%40123@localhost:5432/consent_db')
    cur = conn.cursor()
    
    # Add ROW to region_enum
    print("Adding 'ROW' to region_enum...")
    cur.execute("ALTER TYPE region_enum ADD VALUE IF NOT EXISTS 'ROW'")
    conn.commit()
    
    print("✓ Successfully added 'ROW' to database!")
    
    # Verify
    cur.execute("SELECT unnest(enum_range(NULL::region_enum))::text")
    db_regions = [row[0] for row in cur.fetchall()]
    print(f"\nCurrent regions in DB: {sorted(db_regions)}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
