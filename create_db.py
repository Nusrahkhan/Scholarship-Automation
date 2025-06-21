#from main import app, db
import os
from datetime import datetime
#from models import Student, Admin, Teacher, Circular, TeacherUnavailability, ScholarshipApplication, OTP
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

# Create Flask app
app = Flask(__name__)

# Get absolute paths
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
db_path = os.path.join(instance_path, 'scholarship.db')

# Create instance folder
os.makedirs(instance_path, exist_ok=True)

# Load config
config_path = os.path.join(basedir, 'config.json')
with open(config_path, 'r') as f:
    params = json.load(f)['params']

# Configure app
app.config.update(
    SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=params.get('secret_key', 'default-secret-key')
)

from models import db
db.init_app(app)

from models import Student, Admin, Teacher, Circular, TeacherUnavailability, ScholarshipApplication, OTP


def create_database():
    try:
        with app.app_context():
            for table in [OTP, ScholarshipApplication, TeacherUnavailability, Circular, Teacher, Admin, Student]:
                db.session.query(table).delete()
            db.session.commit()
            print("Cleared all old records from all tables")

            # Create all tables
            db.create_all()
            print("Database tables created successfully!")

            sample_image_path = os.path.join('sample_files', 'sample_circular.jpg')  # or .jpg, .png
            with open(sample_image_path, 'rb') as f:
                file_data = f.read()
            
            admins = [
                Admin(user_id="admin1", password="1"),
                Admin(user_id="admin2", password="2"),
                Admin(user_id="admin3", password="3"),
                Admin(user_id="admin4", password="4"),
                Admin(user_id="admin5", password="5")
            ]
        
            # Add 5 pre-defined teacher users
            teachers = [
                Teacher(username="Teacher One", password="faculty1"),
                Teacher(username="Teacher Two", password="faculty2"),
                Teacher(username="Teacher Three", password="faculty3"),
                Teacher(username="Teacher Four", password="faculty4"),
                Teacher(username="Teacher Five", password="faculty5")
            ]

            sample_circular = Circular(
                title="Welcome to Scholarship Portal",
                description="This is a sample circular to demonstrate the notification system.",
                file_data=file_data,
                filename="sample_circular.jpg",
                created_at=datetime.now(),
            )

            db.session.add_all(admins)
            db.session.add_all(teachers)
            db.session.add(sample_circular)
            db.session.commit()
            print("Sample data added successfully!")
            return True
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        if 'db' in locals():
            db.session.rollback()
        return False


if __name__ == '__main__':
    success = create_database()
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")