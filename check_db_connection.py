#!/usr/bin/env python3
"""Script to check database connection"""
import sys
from sqlalchemy import text
from app.db.database import engine
from app.config import settings

def check_db_connection():
    """Test database connection"""
    print(f"Attempting to connect to database...")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[0]}@***")  # Hide password
    
    try:
        with engine.connect() as connection:
            # Execute a simple query to test connection
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = check_db_connection()
    sys.exit(0 if success else 1)

