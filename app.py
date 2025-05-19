from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from utils import validate_college_email, allowed_file 
import sqlite3
import pyotp
from datetime import datetime, timedelta
from flask_mail import Mail, Message


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarship.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production
# Flask-Mail Config (for sending OTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'  # Use App Password for Gmail
mail = Mail(app)


from models import db, Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication, OTP
db.init_app(app)

# Home Page
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Signup Routes for Student, Teacher, and Admin

# Database connection helper
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# Generate and store OTP (valid for 5 mins)
def generate_and_send_otp(email):
    otp = pyotp.random_base32(length=6)  # 6-digit OTP
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # Store OTP in database
    conn = get_db()
    conn.execute(
        'INSERT INTO otp_store (email, otp, expires_at) VALUES (?, ?, ?)',
        (email, otp, expires_at)
    )
    conn.commit()
    conn.close()
    
    # Send OTP via email
    msg = Message(
        'Your Signup OTP',
        sender='your_email@gmail.com',
        recipients=[email]
    )
    msg.body = f'Your OTP is: {otp} (valid for 5 minutes)'
    mail.send(msg)
    return otp

# Verify OTP
def verify_otp(email, user_otp):
    conn = get_db()
    otp_record = conn.execute(
        'SELECT * FROM otp_store WHERE email = ? AND is_used = FALSE AND expires_at > CURRENT_TIMESTAMP ORDER BY created_at DESC LIMIT 1',
        (email,)
    ).fetchone()
    conn.close()
    
    if otp_record and otp_record['otp'] == user_otp:
        return True
    return False

# Mark OTP as used
def mark_otp_used(email):
    conn = get_db()
    conn.execute(
        'UPDATE otp_store SET is_used = TRUE WHERE email = ?',
        (email,)
    )
    conn.commit()
    conn.close()

# ye student sign up haiii
"""
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
"""

#sign up routes
#student signup and otp
@app.route('/signup', methods=['POST'])
def student_signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    roll_number = data.get('roll_number')

    # Validate college email format
    if not validate_college_email(email):
        return jsonify({
            'error': 'Please use your official college email address in the format: 160XXXYXXXX@mjcollege.ac.in\nExample: 16042175001@mjcollege.ac.in'
        }), 400

    # Password confirmation check
    if 'confirm_password' in data and data['confirm_password'] != password:
        return jsonify({'error': 'Passwords do not match'}), 400

    # Check if email exists
    existing_student = Student.query.filter_by(email=email).first()
    if existing_student:
        return jsonify({'error': 'Email already registered'}), 400

    # Store temporary signup data in session
    session['temp_signup'] = {
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'roll_number': roll_number
    }

    # Generate and send OTP
    try:
        otp = pyotp.random_base32(length=6)
        expires_at = datetime.now() + timedelta(minutes=5)
        
        # Store OTP in database
        new_otp = OTP(
            email=email,
            otp=otp,
            expires_at=expires_at
        )
        db.session.add(new_otp)
        db.session.commit()

        # Send OTP via email
        msg = Message(
            'Your Student Signup OTP',
            sender='noreply@mjcollege.ac.in',
            recipients=[email]
        )
        msg.body = f'Your OTP is: {otp}\nValid for 5 minutes.'
        mail.send(msg)

        return jsonify({
            'message': 'OTP sent to your college email',
            'next_step': '/student/verify-otp'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to send OTP: {str(e)}'}), 500

@app.route('/student_verify-otp', methods=['POST'])
def verify_student_otp():
    data = request.json
    user_otp = data.get('otp')
    
    if 'temp_signup' not in session:
        return jsonify({'error': 'Signup session expired'}), 400

    temp_data = session['temp_signup']
    email = temp_data['email']

    # Verify OTP
    otp_record = OTP.query.filter(
        OTP.email == email,
        OTP.is_used == False,
        OTP.expires_at > datetime.now()
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record or otp_record.otp != user_otp:
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    # Mark OTP as used
    otp_record.is_used = True

    # Create student account
    try:
        new_student = Student(
            username=temp_data['name'],
            email=email,
            password=temp_data['password'],
            roll_number=temp_data['roll_number'],
            is_verified=True
        )
        
        db.session.add(new_student)
        db.session.commit()

        # Clear temp session
        session.pop('temp_signup', None)

        # Set auth session
        session['user_id'] = new_student.user_id
        session['user_type'] = 'student'
        session['username'] = new_student.username

        return jsonify({
            'message': 'Account verified successfully!',
            'redirect': '/student_dashboard'
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Account creation failed: {str(e)}'}), 500

# admin
@app.route('/admin_signup', methods=['POST'])
def admin_signup():
    data = request.json
    username = data.get('username') 
    user_id = data.get('user_id')
    password = data.get('password')

    #Find admin by user_id
    admin = Admin.query.filter_by(user_id=user_id).first()

    if not admin:
        return jsonify({'error': 'Invalid admin ID'}), 400
        
    if not check_password_hash(admin.password, password):
        return jsonify({"error": "Invalid password"}), 401

    # 3. Create admin session
    session['admin_id'] = admin.user_id
    session['admin_username'] = username
    
    return jsonify({
        "message": "Login successful",
        "username": username
    }), 200

#teacher signup
@app.route('/teacher_signup', methods=['POST'])
def teacher_signup():
    data = request.json
    username = data.get('username') 
    user_id = data.get('user_id')
    password = data.get('password')

    #Find admin by user_id
    teacher = Teacher.query.filter_by(user_id=user_id).first()

    if not teacher:
        return jsonify({'error': 'Invalid admin ID'}), 400
        
    if not check_password_hash(teacher.password, password):
        return jsonify({"error": "Invalid password"}), 401

    # 3. Create admin session
    session['teacher_id'] = teacher.user_id
    session['teacher_username'] = username
    
    return jsonify({
        "message": "Login successful",
        "username": username
    }), 200


"""
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
"""

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
"""
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
"""

# student dashboard route
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

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/teacher_login')
def teacher_login():
    return render_template('teacher_login.html')

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


# Time table insertion
@app.route('/upload_timetable', methods=['POST'])
def upload_timetable():
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'timetable' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['timetable']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Get the current teacher
        teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404
    #Read the file data
    file_data = file.read()
        
    # Update the teacher record
    teacher.time_table = file_data
    teacher.time_table_filename = file.filename

    try:
        db.session.commit()
        return jsonify({'message': 'Timetable uploaded successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

        

@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug = True, port = 8000)

