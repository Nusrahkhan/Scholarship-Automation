import sqlite3
import os
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    """Connect to the application's configured database."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    """Initialize the database."""
    db = get_db()

    # Create student_info table for consistency checks
    db.execute('''
    CREATE TABLE IF NOT EXISTS student_info (
        student_id TEXT PRIMARY KEY,
        reference_name TEXT,
        reference_roll_no TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create updated verification_results table
    db.execute('''
    CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        document_id TEXT UNIQUE NOT NULL,
        task_id TEXT UNIQUE NOT NULL,
        document_type TEXT NOT NULL,
        status TEXT NOT NULL,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES student_info (student_id)
    )
    ''')

    db.commit()

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)

    # Initialize database when app starts
    with app.app_context():
        init_db()
