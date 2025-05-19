from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from utils import validate_college_email

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarship.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production

from models import db, Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication
db.init_app(app)

# Home Page
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Signup Routes for Student, Teacher, and Admin

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name') 
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
    

@app.route('/admin_signup', methods=['POST'])
def admin_signup():
    data = request.json
    name = data.get('name') 
    email = data.get('email')
    password = data.get('password')

    # Validate email format using our custom validator
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if passwords match (if confirm password is sent)
    if 'confirm_password' in data and data['confirm_password'] != password:
        return jsonify({'error': 'Passwords do not match'}), 400

    # Check if email already exists
    existing_admin = Admin.query.filter_by(email=email).first()
    if existing_admin:
        return jsonify({'error': 'Email already registered'}), 400

    # Hash the password
    password_hash = generate_password_hash(password)

    # Create new teacher
    new_admin = Admin(
        username=name,
        email=email,
        password=password_hash,
    )

    # Insert user into database
    try:
        db.session.add(new_admin)
        db.session.commit()

        # Set up a session for the newly registered teacher user
        session['user_id'] = new_admin.user_id
        session['user_type'] = 'admin'
        session['username'] = new_admin.username

        return jsonify({
            'message': 'Registration successful! You can now login.',
            'redirect': '/admin_dashboard'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    

@app.route('/teacher_signup', methods=['POST'])
def teacher_signup():
    data = request.json
    name = data.get('name') 
    email = data.get('email')
    password = data.get('password')

    # Validate email format using our custom validator
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if passwords match (if confirm password is sent)
    if 'confirm_password' in data and data['confirm_password'] != password:
        return jsonify({'error': 'Passwords do not match'}), 400

    # Check if email already exists
    existing_teacher = Teacher.query.filter_by(email=email).first()
    if existing_teacher:
        return jsonify({'error': 'Email already registered'}), 400

    # Hash the password
    password_hash = generate_password_hash(password)

    # Create new teacher
    new_teacher = Teacher(
        username=name,
        email=email,
        password=password_hash,
    )

    # Insert user into database
    try:
        db.session.add(new_teacher)
        db.session.commit()

        # Set up a session for the newly registered teacher user
        session['user_id'] = new_teacher.user_id
        session['user_type'] = 'teacher'
        session['username'] = new_teacher.username

        return jsonify({
            'message': 'Registration successful! You can now login.',
            'redirect': '/teacher_dashboard'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

#Login Routes for Student, Teacher, and Admin

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

@app.route('/teacher_login', methods=['POST', 'GET'])
def teacher_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Validate email format
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if user exists
    teacher = Teacher.query.filter_by(email=email).first()
    if not teacher:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not check_password_hash(teacher.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Set up session
    session['user_id'] = teacher.user_id
    session['user_type'] = 'teacher'
    session['username'] = teacher.username

    return jsonify({
        'message': 'Login successful!',
        'redirect': '/teacher_dashboard'
    })

@app.route('/admin_login', methods=['POST', 'GET'])
def admin_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Validate email format
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Check if user exists
    admin = Admin.query.filter_by(email=email).first()
    if not admin:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify password
    if not check_password_hash(admin.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Set up session
    session['user_id'] = admin.user_id
    session['user_type'] = 'admin'
    session['username'] = admin.username

    return jsonify({
        'message': 'Login successful!',
        'redirect': '/admin_dashboard'
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

