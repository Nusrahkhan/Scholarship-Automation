from app import app, db
import os
from datetime import datetime
from models import Student, Admin, Teacher, Circular, TeacherUnavailability, ScholarshipApplication, OTP

def create_database():
    with app.app_context():
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


if __name__ == '__main__':
    create_database()