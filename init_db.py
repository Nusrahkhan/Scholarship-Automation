from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json

# Create Flask app
app = Flask(__name__)

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
with open(config_path, 'r') as f:
    params = json.load(f)['params']

# Get absolute paths
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
db_path = os.path.join(instance_path, 'scholarship.db')

# Create instance folder if it doesn't exist
os.makedirs(instance_path, exist_ok=True)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = params.get('secret_key', 'default-secret-key')

# Initialize database
db = SQLAlchemy(app)

from models import Student, Admin, Teacher, Circular, TeacherUnavailability, ScholarshipApplication, OTP

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

        try:
            # Add admin users
            admins = [
                Admin(user_id=f"admin{i}", password=str(i)) 
                for i in range(1, 6)
            ]
            
            # Add teacher users
            teachers = [
                Teacher(username=f"Teacher {i}", password=f"faculty{i}") 
                for i in range(1, 6)
            ]

            # Add sample circular if exists
            sample_image_path = os.path.join('sample_files', 'sample_circular.jpg')
            if os.path.exists(sample_image_path):
                with open(sample_image_path, 'rb') as f:
                    file_data = f.read()
                    circular = Circular(
                        title="Welcome to Scholarship Portal",
                        description="Sample circular",
                        file_data=file_data,
                        filename="sample_circular.jpg"
                    )
                    db.session.add(circular)

            # Add all data
            db.session.add_all(admins)
            db.session.add_all(teachers)
            db.session.commit()
            print("Sample data added successfully!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"Error adding sample data: {str(e)}")
            return False

if __name__ == '__main__':
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database")

    # Initialize new database
    if init_database():
        print("Database initialization completed successfully!")
    else:
        print("Database initialization failed!")