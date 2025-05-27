#!/usr/bin/env python3
"""
Database migration script to update existing schema to support new features.
"""

import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_database():
    """Migrate existing database to new schema."""
    # Get database path from environment variable
    db_path = os.getenv('DATABASE_PATH', 'app/db/results.db')
    
    if not os.path.exists(db_path):
        print("No existing database found. Creating new database with updated schema.")
        from app.db.setup import setup_database
        setup_database()
        return
    
    print(f"Migrating database at {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if student_info table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='student_info'")
        if not cursor.fetchone():
            print("Creating student_info table...")
            cursor.execute('''
            CREATE TABLE student_info (
                student_id TEXT PRIMARY KEY,
                reference_name TEXT,
                reference_roll_no TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        
        # Check if verification_results has the new columns
        cursor.execute("PRAGMA table_info(verification_results)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns if they don't exist
        if 'student_id' not in columns:
            print("Adding student_id column to verification_results...")
            cursor.execute("ALTER TABLE verification_results ADD COLUMN student_id TEXT")
        
        if 'document_type' not in columns:
            print("Adding document_type column to verification_results...")
            cursor.execute("ALTER TABLE verification_results ADD COLUMN document_type TEXT DEFAULT 'unknown'")
        
        # Update existing records with default document_type if needed
        cursor.execute("UPDATE verification_results SET document_type = 'aadhaar' WHERE document_type IS NULL OR document_type = 'unknown'")
        
        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
