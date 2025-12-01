"""Debug script to run migration and capture detailed error information"""
import sys
import traceback
from sqlalchemy import create_engine, text
from sqlalchemy.exc import InternalError, OperationalError
from alembic import command
from alembic.config import Config

def debug_migration():
    """Run migration with detailed error logging"""
    try:
        # Load Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        print("=" * 80)
        print("Starting migration with debug logging...")
        print("=" * 80)
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        print("=" * 80)
        print("Migration completed successfully!")
        print("=" * 80)
        
    except InternalError as e:
        print("\n" + "=" * 80)
        print("INTERNAL ERROR (Transaction Aborted):")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Original Exception: {e.orig}")
        print(f"SQL Statement: {getattr(e, 'statement', 'N/A')}")
        print(f"Parameters: {getattr(e, 'params', 'N/A')}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
        # Try to get more details from the connection
        try:
            if hasattr(e, 'connection'):
                print("\nConnection State:")
                print(f"  Is Closed: {e.connection.closed if hasattr(e.connection, 'closed') else 'N/A'}")
        except:
            pass
            
    except OperationalError as e:
        print("\n" + "=" * 80)
        print("OPERATIONAL ERROR:")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Original Exception: {e.orig}")
        print(f"SQL Statement: {getattr(e, 'statement', 'N/A')}")
        print(f"Parameters: {getattr(e, 'params', 'N/A')}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("UNEXPECTED ERROR:")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
        # Check if it's a transaction abort error
        error_str = str(e).lower()
        if "current transaction is aborted" in error_str or "transaction" in error_str:
            print("\n⚠️  This appears to be a transaction abort error!")
            print("   An earlier operation in the migration likely failed.")
            print("   Check the migration code for operations that might fail silently.")
        
    finally:
        print("\n" + "=" * 80)
        print("Debug session ended")
        print("=" * 80)

if __name__ == "__main__":
    debug_migration()
