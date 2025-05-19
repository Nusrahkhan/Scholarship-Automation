from app import app, db
from models import Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication, OTP

def create_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
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

        db.session.add_all(admins)
        db.session.add_all(teachers)
        db.session.commit()


if __name__ == '__main__':
    create_database()