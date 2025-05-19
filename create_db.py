from app import app, db
from models import Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication, OTP

def create_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    create_database()