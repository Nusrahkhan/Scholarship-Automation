from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from utils import validate_college_email, allowed_file 
import sqlite3
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import json
import random
from models import db, Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication, OTP, Circular


app = Flask(__name__)

with open('config.json', 'r') as f:
    params = json.load(f)['params']

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scholarship.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this in production
# Flask-Mail Config (for sending OTP)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = params['gmail-user']
app.config['MAIL_PASSWORD'] = params['gmail-password']  # Use App Password for Gmail
mail = Mail(app)


db.init_app(app)

# Home Page
@app.route('/')
def index():
    if 'user_id' in session and session.get('user_type') == 'student':
        return redirect('/student_dashboard')
    elif 'admin_id' in session and session.get('user_type') == 'admin':
        return redirect('/admin_dashboard')
    elif 'teacher_id' in session and session.get('user_type') == 'teacher':
        return redirect('/faculty_dashboard')
    return render_template('index.html')

# Signup Routes for Student, Teacher, and Admin

# Database connection helper
def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


# Mark OTP as used
def mark_otp_used(email):
    conn = get_db()
    conn.execute(
        'DELETE FROM otp_store WHERE email = ?',
        (email,)
    )
    # Delete old/used OTPs
    conn.execute('''
        DELETE FROM otp_store 
        WHERE (is_used = TRUE) 
        OR (expires_at < datetime('now'))
    ''')

    conn.commit()
    conn.close()


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

        # **NEW: Check for existing OTP within 5 minutes (Rate Limiting)**
    existing_otp = OTP.query.filter(
        OTP.email == email,
        OTP.created_at > datetime.now() - timedelta(minutes=5),
        OTP.is_used == False
    ).first()

    if existing_otp:
        time_remaining = 5 - (datetime.now() - existing_otp.created_at).total_seconds() / 60
        return jsonify({
            'error': f'OTP already sent! Please wait {int(time_remaining)} more minutes before requesting a new OTP.',
            'time_remaining': int(time_remaining)
        }), 429

    # Store temporary signup data in session
    session['temp_signup'] = {
        'name': name,
        'email': email,
        'password': generate_password_hash(password),
        'roll_number': roll_number
    }

    # Generate and send OTP
    try:
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
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
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f'Your OTP is: {otp}\nValid for 5 minutes.'
        mail.send(msg)

        return jsonify({
            'message': 'OTP sent to your college email',
            'next_step': 'verify-otp'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to send OTP: {str(e)}'}), 500

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    user_otp = data.get('otp')
    
    if 'temp_signup' not in session:
        return jsonify({'error': 'Signup session expired'}), 400

    temp_data = session['temp_signup']
    email = temp_data['email']

    cleanup_otps()  # Clean up old/used OTPs before verification

    # Verify OTP
    otp_record = OTP.query.filter(
        OTP.email == email,
        OTP.is_used == False,
        OTP.expires_at > datetime.now()
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record or otp_record.otp != user_otp:
        return jsonify({'error': 'Invalid or expired OTP'}), 400
    
    # Delete the OTP immediately after successful verification
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

def cleanup_otps():
    """Clean up used and expired OTPs"""
    try:
        # Delete used OTPs
        OTP.query.filter_by(is_used=True).delete()
        
        # Delete expired OTPs
        OTP.query.filter(OTP.expires_at < datetime.now()).delete()
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error cleaning up OTPs: {str(e)}")


@app.route('/verify')
def verify_page():
    if 'temp_signup' not in session:
        return redirect(url_for('index'))
    return render_template('verify.html')

# faculty and admin logins based on password given already
# admin login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')

    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    #Find admin by user_id
    admin = Admin.query.filter_by(user_id=user_id).first()

    if not admin:
        return jsonify({'error': 'Invalid admin ID'}), 400
        
    if admin.password != password:
        return jsonify({"error": "Invalid password"}), 401

    # 3. Create admin session
    session['admin_id'] = admin.user_id
    session['user_type'] = 'admin'
    session['admin_username'] = admin.user_id
    
    return jsonify({
        "message": "Login successful",
        "username": admin.user_id
    }), 200

# faculty login
@app.route('/faculty_login', methods=['GET', 'POST'])
def faculty_login():
    if request.method == 'GET':
        return render_template('faculty_login.html')
    
    data = request.json
    username = data.get('username')
    password = data.get('password')
    print (f"idarrr {password}")

    #Find admin by user_id
    teacher = Teacher.query.filter_by(username=username).first()
    print(teacher)

    if not teacher:
        return jsonify({'error': 'Invalid admin ID'}), 400
        
    if teacher.password != password:
        return jsonify({"error": "Invalid password"}), 401

    # 3. Create admin session
    session['teacher_id'] = teacher.user_id
    session['user_type'] = 'teacher'
    session['teacher_username'] = teacher.username
    
    return jsonify({
        "message": "Login successful",
        "username": username,
    }), 200


# dashboard route
# faculty dashboard route
@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'teacher_id' not in session:
        return redirect(url_for('index'))

    return render_template('faculty_dashboard.html', username=session.get('username'))

#admin dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('index'))

    return render_template('admin_dashboard.html', username=session.get('username'))

#student dashboard route
@app.route('/student_dashboard')
def student_dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Check if user is a student
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))
    
        # Verify student exists in database
    student = Student.query.get(session['user_id'])
    if not student:
        # Invalid session - clear it and redirect
        session.clear()
        return redirect(url_for('index'))

    # Render the student dashboard
    return render_template('student_dashboard.html', username=session.get('username', 'Student'))


#Login Routes for Student
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

# student dashboard route


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


# ye idk
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
    if 'teacher_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if 'timetable' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files.get('timetable')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    allowed = file.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png'))
    if not allowed:
        return jsonify({'error': 'Invalid file type'}), 400

    #Read the file data
    file_data = file.read()
    filename = file.filename

    # Get the current teacher
    teacher = db.session.get(Teacher, session['teacher_id'])
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    # Update the teacher record
    teacher.time_table = file_data
    teacher.time_table_filename = filename

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Timetable uploaded successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# saving unavailability dates
@app.route('/save_unavailability', methods=['POST'])
def save_unavailability():
    if 'teacher_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    dates = data.get('dates', [])
    teacher = db.session.get(Teacher, session['teacher_id'])
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    # Optional: Remove previous unavailability for this teacher
    TeacherUnavailability.query.filter_by(username=teacher.username).delete()

    # Add new unavailable dates
    for date_str in dates:
        entry = TeacherUnavailability(username=teacher.username, date=date_str)
        db.session.add(entry)

    try:
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# circular routes
@app.route('/upload_circular', methods=['POST'])
def upload_circular():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('circular_file')

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        circular = Circular(
            title=title,
            description=description
        )

        if file:
            filename = secure_filename(file.filename)
            circular.filename = filename
            circular.file_data = file.read()

        db.session.add(circular)
        db.session.commit()

        return jsonify({
            'message': 'Circular uploaded successfully',
            'circular': {
                'title': circular.title,
                'description': circular.description,
                'has_attachment': bool(circular.file_data)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/get_circulars')
def get_circulars():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    circulars = Circular.query.filter_by(is_active=True).order_by(Circular.created_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'title': c.title,
        'description': c.description,
        'created_at': c.created_at.strftime('%d-%m-%Y'),
        'has_attachment': bool(c.file_data)
    } for c in circulars]), 200

@app.route('/circular_file/<int:circular_id>')
def get_circular_file(circular_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    circular = Circular.query.get_or_404(circular_id)
    
    if not circular.file_data:
        return jsonify({'error': 'No file attached'}), 404

    response = make_response(circular.file_data)
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Disposition'] = f'attachment; filename={circular.filename}'
    return response


@app.route('/get_timetable/<int:teacher_id>')
def get_timetable(teacher_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    teacher = Teacher.query.get_or_404(teacher_id)
    
    if not teacher.time_table:
        return jsonify({'error': 'No timetable found'}), 404

    response = make_response(teacher.time_table)
    file_ext = teacher.time_table_filename.split('.')[-1].lower()
    
    content_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png'
    }
    
    response.headers['Content-Type'] = content_types.get(file_ext, 'application/octet-stream')
    response.headers['Content-Disposition'] = f'inline; filename={teacher.time_table_filename}'
    return response


@app.route('/available_teachers', methods=['GET'])
def available_teachers():
    """Handle both API and view requests for available teachers"""
    # Get date parameter or use current date
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Check if requesting JSON (API) or HTML (view)
    want_json = request.headers.get('Accept') == 'application/json'
    
    try:
        datetime.strptime(selected_date, '%Y-%m-%d')
    except ValueError:
        if want_json:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        return "Invalid date format. Use YYYY-MM-DD", 400

    # Get unavailable teacher IDs
    unavailable_teacher_ids = [
        t.user_id for t in TeacherUnavailability.query.filter_by(date=selected_date).all()
    ]
    # Get available teachers
    available_teachers = Teacher.query.filter(
        Teacher.user_id.notin_(unavailable_teacher_ids) if unavailable_teacher_ids else True
    ).all()

    if want_json:
        # Return JSON response for API
        teachers_data = [{
            'user_id': teacher.user_id,
            'username': teacher.username,
            'has_timetable': teacher.time_table is not None,
            'timetable_url': url_for('get_timetable', teacher_id=teacher.user_id, _external=True) 
                           if teacher.time_table else None
        } for teacher in available_teachers]

        return jsonify({
            'date': selected_date,
            'available_teachers': teachers_data
        })
    else:
        # Return HTML view
        return render_template('available_teachers.html',
                            teachers=available_teachers,
                            selected_date=selected_date)

@app.route('/upload_doc')
def upload_doc():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('index'))
    return render_template('upload_doc.html')

# logout     
@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

# Document list route
@app.route('/list_of_doc')
def list_of_doc():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Check if user is a student
    if session.get('user_type') != 'student':
        return redirect(url_for('index'))

    # Render the document list page
    return render_template('list_of_doc.html')

if __name__ == '__main__':
    app.run(debug = True, port = 8000)
