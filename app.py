from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import re
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarship.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production
db = SQLAlchemy(app)

# Email validation function
def validate_college_email(email):
    """
    Validates that the email follows the college email format:
    160(d2)(d7)(d5)@mjcollege.ac.in
    Where d2 is a 2-digit number, d7 is a 1-digit number, and d5 is a 5-digit number
    """
    pattern = r'^16042\d{1}\d{1}\d{5}@mjcollege\.ac\.in$'
    if not re.match(pattern, email):
        return False
    return True

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

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')  # This matches what the frontend is sending
    email = data.get('email')
    password = data.get('password')
    roll_number = data.get('roll_number')

    # Validate email format using our custom validator
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if passwords match (if confirm password is sent)
    if 'confirm_password' in data and data['confirm_password'] != password:
        return jsonify({'error': 'Passwords do not match'}), 400

    # Check if email already exists
    existing_student = Student.query.filter_by(email=email).first()
    if existing_student:
        return jsonify({'error': 'Email already registered'}), 400

    # Hash the password
    password_hash = generate_password_hash(password)

    # Create new student
    new_student = Student(
        username=name,
        email=email,
        password=password_hash,
        roll_number=roll_number
    )

    # Insert user into database
    try:
        db.session.add(new_student)
        db.session.commit()

        # Set up a session for the newly registered user
        session['user_id'] = new_student.user_id
        session['user_type'] = 'student'
        session['username'] = new_student.username

        return jsonify({
            'message': 'Registration successful! You can now login.',
            'redirect': '/student_dashboard'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@app.route('/login', methods=['POST', 'GET'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Validate email format
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if user exists
    student = Student.query.filter_by(email=email).first()
    if not student:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not check_password_hash(student.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Set up session
    session['user_id'] = student.user_id
    session['user_type'] = 'student'
    session['username'] = student.username

    return jsonify({
        'message': 'Login successful!',
        'redirect': '/student_dashboard'
    })

@app.route('/student_dashboard')
def student_dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Check if user is a student
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))

    # Render the student dashboard
    return render_template('student_dasboard.html', username=session.get('username', 'Student'))

@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Render dashboard based on user type
    if session.get('user_type') == 'student':
        return redirect(url_for('student_dashboard'))
    elif session.get('user_type') == 'admin':
        return render_template('admin_dashboard.html', username=session.get('username', 'Admin'))
    elif session.get('user_type') == 'teacher':
        return render_template('teacher_dashboard.html', username=session.get('username', 'Teacher'))

    # Fallback
    return redirect(url_for('index'))

@app.route('/api/user')
def get_user_data():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Get user data based on user type
    if session.get('user_type') == 'student':
        student = Student.query.filter_by(user_id=session.get('user_id')).first()
        if not student:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'name': student.username,
            'email': student.email,
            'roll_number': student.roll_number,
            'user_type': 'student'
        })

    # For other user types (admin, teacher)
    return jsonify({
        'name': session.get('username', 'User'),
        'user_type': session.get('user_type', 'unknown')
    })

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug = True, port = 8000)

