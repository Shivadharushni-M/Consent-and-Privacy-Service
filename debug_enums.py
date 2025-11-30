"""Debug script to check enum mismatches between code and database"""
import psycopg2
from app.models.consent import RegionEnum, PurposeEnum

try:
    # URL-encode the @ in password: shiva@123 -> shiva%40123
    conn = psycopg2.connect('postgresql://postgres:shiva%40123@localhost:5432/consent_db')
    cur = conn.cursor()
    
    # Get DB enums
    cur.execute("SELECT unnest(enum_range(NULL::region_enum))::text")
    db_regions = [row[0] for row in cur.fetchall()]
    
    cur.execute("SELECT unnest(enum_range(NULL::purpose_enum))::text")
    db_purposes = [row[0] for row in cur.fetchall()]
    
    conn.close()
    
    print('=' * 60)
    print('DATABASE ENUMS')
    print('=' * 60)
    print(f'DB Regions: {sorted(db_regions)}')
    print(f'DB Purposes: {sorted(db_purposes)}')
    print()
    
    print('=' * 60)
    print('CODE ENUMS')
    print('=' * 60)
    code_regions = [e.value for e in RegionEnum]
    code_purposes = [e.value for e in PurposeEnum]
    print(f'Code Regions: {sorted(code_regions)}')
    print(f'Code Purposes: {sorted(code_purposes)}')
    print()
    
    print('=' * 60)
    print('MISMATCHES')
    print('=' * 60)
    
    # Check regions
    code_regions_set = set(code_regions)
    db_regions_set = set(db_regions)
    missing_in_db_regions = code_regions_set - db_regions_set
    extra_in_db_regions = db_regions_set - code_regions_set
    
    if missing_in_db_regions:
        print(f'❌ Regions in CODE but NOT in DB: {missing_in_db_regions}')
    if extra_in_db_regions:
        print(f'⚠️  Regions in DB but NOT in CODE: {extra_in_db_regions}')
    if not missing_in_db_regions and not extra_in_db_regions:
        print('✓ All regions match!')
    
    print()
    
    # Check purposes
    code_purposes_set = set(code_purposes)
    db_purposes_set = set(db_purposes)
    missing_in_db_purposes = code_purposes_set - db_purposes_set
    extra_in_db_purposes = db_purposes_set - code_purposes_set
    
    if missing_in_db_purposes:
        print(f'❌ Purposes in CODE but NOT in DB: {missing_in_db_purposes}')
    if extra_in_db_purposes:
        print(f'⚠️  Purposes in DB but NOT in CODE: {extra_in_db_purposes}')
    if not missing_in_db_purposes and not extra_in_db_purposes:
        print('✓ All purposes match!')
    
    print()
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
