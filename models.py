from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class Student(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)
    roll_number = db.Column(db.String(80), unique=True, nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"Student('{self.username}', '{self.email}')"

class Admin(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"Admin('{self.username}', '{self.email}')"

class Teacher(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    time_table = db.Column(db.Text)

    def __repr__(self) -> str:
        return f"Teacher('{self.username}', '{self.email}')"

class TeacherUnavailability(db.Model):
    user_id = db.Column(db.Integer,primary_key = True, nullable=False, autoincrement=True)
    username = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(80), nullable=False)

    def __repr__(self) -> str:
        return f"TeacherUnavailability('{self.username}', '{self.date}')"

class ScholarshipApplication(db.Model):
    user_id = db.Column(db.Integer,primary_key = True, nullable=False, autoincrement=True)
    roll_number = db.Column(db.String(80), nullable=False)
    scholarship_state = db.Column(db.String(80))

    def __repr__(self) -> str:
        return f"ScholarshipApplication('{self.roll_number}', '{self.scholarship_state}')"
