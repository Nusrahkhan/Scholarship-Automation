import os
import tempfile
import pytest
from app import create_app
from app.db.db import init_db

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app({
        'TESTING': True,
        'DATABASE_PATH': db_path,
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'REDIS_URL': 'memory://',  # Use in-memory broker for testing
    })
    
    # Create the database and load test data
    with app.app_context():
        init_db()
    
    yield app
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()
