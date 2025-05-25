from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Student(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)
    roll_number = db.Column(db.String(80), unique=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f"Student('{self.username}', '{self.email}')"

class Admin(db.Model):
    user_id = db.Column(db.String(80), primary_key=True)
    password = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"Admin('{self.username}')"

class Teacher(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)
    time_table = db.Column(db.LargeBinary)  
    time_table_filename = db.Column(db.String(255)) 

    def __repr__(self) -> str:
        return f"Teacher('{self.username}')"

class TeacherUnavailability(db.Model):
    user_id = db.Column(db.Integer,primary_key = True, nullable=False, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)

    def __repr__(self) -> str:
        return f"TeacherUnavailability('{self.username}', '{self.date}')"

class ScholarshipApplication(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    roll_number = db.Column(db.String(80), nullable=False)
    branch = db.Column(db.String(80), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    lateral_entry = db.Column(db.Boolean, default=False)  # LE field
    scholarship_state = db.Column(db.String(80), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


    def __repr__(self) -> str:
        return f"ScholarshipApplication('{self.roll_number}', '{self.scholarship_state}')"
    
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp = db.Column(db.String(16), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

# This table consists of the circulars that are sent to the students
class Circular(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    file_data = db.Column(db.LargeBinary)
    filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"Circular('{self.title}', '{self.created_at}')"