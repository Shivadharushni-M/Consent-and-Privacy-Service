"""Simple debug script to see the actual migration error"""
import sys
import traceback

# Add the project directory to the path
sys.path.insert(0, '.')

try:
    from alembic import command
    from alembic.config import Config
    
    print("Loading Alembic configuration...")
    alembic_cfg = Config("alembic.ini")
    
    print("Starting migration upgrade...")
    print("-" * 80)
    
    # This will show us the actual error
    command.upgrade(alembic_cfg, "head")
    
    print("-" * 80)
    print("Migration completed successfully!")
    
except Exception as e:
    print("\n" + "=" * 80)
    print("ERROR CAUGHT:")
    print("=" * 80)
    print(f"Exception Type: {type(e).__name__}")
    print(f"Exception Message: {str(e)}")
    
    # Get the original exception if it's wrapped
    if hasattr(e, 'orig'):
        print(f"\nOriginal Exception Type: {type(e.orig).__name__}")
        print(f"Original Exception: {e.orig}")
        if hasattr(e.orig, 'pgcode'):
            print(f"PostgreSQL Error Code: {e.orig.pgcode}")
        if hasattr(e.orig, 'pgerror'):
            print(f"PostgreSQL Error Message: {e.orig.pgerror}")
    
    # Get SQL statement if available
    if hasattr(e, 'statement'):
        print(f"\nSQL Statement: {e.statement}")
    if hasattr(e, 'params'):
        print(f"SQL Parameters: {e.params}")
    
    print("\n" + "=" * 80)
    print("FULL TRACEBACK:")
    print("=" * 80)
    traceback.print_exc()
    
    # Check for transaction abort
    error_str = str(e).lower()
    if "current transaction is aborted" in error_str:
        print("\n" + "=" * 80)
        print("⚠️  TRANSACTION ABORT DETECTED!")
        print("=" * 80)
        print("This means an earlier SQL operation failed and aborted the transaction.")
        print("The error above shows WHERE the abort was detected, not WHERE it started.")
        print("\nTo find the actual failing operation:")
        print("1. Look at the migration file: alembic/versions/009_fix_audit_logs_id_to_uuid.py")
        print("2. Check the line number in the traceback")
        print("3. The actual failure happened BEFORE that line")
        print("=" * 80)
