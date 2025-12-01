"""Detailed debug script to trace migration operations step by step"""
import sys
import traceback
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import InternalError, OperationalError
from alembic import command
from alembic.config import Config
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a logger
logger = logging.getLogger('migration_debug')

def setup_sql_logging():
    """Set up SQL statement logging"""
    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        logger.info("=" * 80)
        logger.info("EXECUTING SQL:")
        logger.info(f"Statement: {statement}")
        logger.info(f"Parameters: {parameters}")
        logger.info("=" * 80)
    
    @event.listens_for(Engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if hasattr(cursor, 'rowcount'):
            logger.info(f"Rows affected: {cursor.rowcount}")
    
    @event.listens_for(Engine, "handle_error")
    def receive_handle_error(exception_context):
        logger.error("=" * 80)
        logger.error("SQL ERROR DETECTED:")
        logger.error(f"Exception: {exception_context.exception}")
        logger.error(f"Statement: {exception_context.statement}")
        logger.error(f"Parameters: {exception_context.parameters}")
        logger.error("=" * 80)

def debug_migration_detailed():
    """Run migration with step-by-step debugging"""
    try:
        # Set up SQL logging
        setup_sql_logging()
        
        # Load Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        print("=" * 80)
        print("Starting detailed migration debugging...")
        print("All SQL statements will be logged")
        print("=" * 80)
        print()
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        print()
        print("=" * 80)
        print("✅ Migration completed successfully!")
        print("=" * 80)
        
    except InternalError as e:
        print("\n" + "=" * 80)
        print("❌ INTERNAL ERROR (Transaction Aborted):")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        if hasattr(e, 'orig'):
            print(f"Original Exception Type: {type(e.orig).__name__}")
            print(f"Original Exception: {e.orig}")
            if hasattr(e.orig, 'pgcode'):
                print(f"PostgreSQL Error Code: {e.orig.pgcode}")
            if hasattr(e.orig, 'pgerror'):
                print(f"PostgreSQL Error Message: {e.orig.pgerror}")
        print(f"SQL Statement: {getattr(e, 'statement', 'N/A')}")
        print(f"Parameters: {getattr(e, 'params', 'N/A')}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
        # Analyze the error
        error_str = str(e).lower()
        if "current transaction is aborted" in error_str:
            print("\n🔍 ANALYSIS:")
            print("   The transaction was aborted by an earlier operation.")
            print("   Look at the SQL statements logged above to find which one failed.")
            print("   The failing operation likely:")
            print("   - Tried to access a non-existent column/table/index")
            print("   - Violated a constraint")
            print("   - Referenced a missing object")
        
    except OperationalError as e:
        print("\n" + "=" * 80)
        print("❌ OPERATIONAL ERROR:")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        if hasattr(e, 'orig'):
            print(f"Original Exception: {e.orig}")
        print(f"SQL Statement: {getattr(e, 'statement', 'N/A')}")
        print(f"Parameters: {getattr(e, 'params', 'N/A')}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ UNEXPECTED ERROR:")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nFull Traceback:")
        traceback.print_exc()
        print("=" * 80)
        
    finally:
        print("\n" + "=" * 80)
        print("Debug session ended")
        print("=" * 80)
        print("\n💡 TIP: Check the logs above to see all SQL statements executed.")
        print("   The error occurred after one of those statements failed.")

if __name__ == "__main__":
    debug_migration_detailed()
