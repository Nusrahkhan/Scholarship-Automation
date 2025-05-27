import os
from flask import Flask
from flask_restful import Api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Configure app
    app.config.from_mapping(
        SECRET_KEY='dev',
        UPLOAD_FOLDER=os.getenv('UPLOAD_FOLDER', 'app/static/uploads'),
        DATABASE_PATH=os.getenv('DATABASE_PATH', 'app/db/results.db'),
        REDIS_URL=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        TESSERACT_PATH=os.getenv('TESSERACT_PATH', '/usr/bin/tesseract'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max upload size
    )

    if test_config is not None:
        # Load test config if passed
        app.config.from_mapping(test_config)

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialize API
    api = Api(app)

    # Register routes
    from app.routes.api import init_app as init_routes
    init_routes(api)

    # Initialize database
    from app.db.db import init_app as init_db
    init_db(app)

    return app
