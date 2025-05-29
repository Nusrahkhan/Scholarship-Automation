import os
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up the SQLite database."""
    # Get database path from environment variable
    db_path = os.getenv('DATABASE_PATH', 'app/db/results.db')

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create student_info table for consistency checks
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS student_info (
        student_id TEXT PRIMARY KEY,
        reference_name TEXT,
        reference_roll_no TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create updated verification_results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        document_id TEXT UNIQUE NOT NULL,
        task_id TEXT UNIQUE NOT NULL,
        document_type TEXT NOT NULL,
        student_category TEXT,
        status TEXT NOT NULL,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES student_info (student_id)
    )
    ''')

    # Add student_category column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE verification_results ADD COLUMN student_category TEXT')
        print("Added student_category column to existing verification_results table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Commit changes and close connection
    conn.commit()
    conn.close()

    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    setup_database()
