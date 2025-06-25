from flask import Flask, request, jsonify, render_template, session, abort, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import sys
import random
from dotenv import load_dotenv, dotenv_values
from sqlalchemy import distinct, extract, desc, func
from document_verification import *

from flask_cors import CORS  # <-- ✅ Add this line

app = Flask(__name__)
CORS(app)  # <-- ✅ Add this line just after app is initialized




# Database configuration - use absolute paths
basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
db_path = os.path.join(instance_path, 'scholarship.db')
upload_path = os.path.join(basedir, 'static', 'uploads')
os.makedirs(instance_path, exist_ok=True)
os.makedirs(upload_path, exist_ok=True)

#load configuration from config.json
config_path = os.path.join(basedir, 'config.json')
with open(config_path, 'r') as f:
    params = json.load(f)['params']

# Generate a secure secret key if not exists
if not params.get('secret_key'):
    import secrets
    params['secret_key'] = secrets.token_hex(32)
    # Save back to config.json
    with open(config_path, 'w') as f:
        json.dump({'params': params}, f, indent=4)


# Flask Configuration
app.config.update(
    SECRET_KEY=params['secret_key'],
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
    SQLALCHEMY_DATABASE_URI=f'sqlite:///{db_path}',  # Fixed database path
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password'],
    UPLOAD_FOLDER=os.path.join(basedir, 'static', 'uploads'),  # Fixed upload path
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    ALLOWED_EXTENSIONS={'pdf', 'png', 'jpg', 'jpeg'}
)


from models import db
db.init_app(app)
mail = Mail(app)

#app.app_context().push()

from models import Student, Admin, Teacher, TeacherUnavailability, ScholarshipApplication, OTP, Circular, Appointment

# Add OCR model to Python path
ocr_model_path = os.path.join(os.path.dirname(__file__), 'ocr_model')
sys.path.append(ocr_model_path)

# Load environment variables from .env (force override)
dotenv_path = os.path.join(ocr_model_path, 'ocr_model', '.env')
#print('[ENV] .env path:', dotenv_path, 'Exists:', os.path.exists(dotenv_path))
load_dotenv(dotenv_path, override=True)
#print('[ENV] GEMINI_API_KEY loaded:', os.getenv('GEMINI_API_KEY'))

# Print raw .env file contents for debugging
#with codecs.open(dotenv_path, 'r', encoding='utf-8-sig') as f:
 #   env_contents = f.read()
  #  print('[ENV] Raw .env contents:', repr(env_contents))
# Print parsed .env values
#parsed_env = dotenv_values(dotenv_path)
#print('[ENV] dotenv_values parsed:', parsed_env)

#import utility functions
from utils import validate_college_email, allowed_file


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

#ocr model helper functions
import os
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# check all documents are verified or not
"""
def check_all_documents_verified(student_id):
    #Check if all required documents are verified for the student's latest application.
    try:
        # Get student info
        student = db.session.get(Student, session['user_id'])
        if not student:
            return False, "Student not found"

        # Get latest scholarship application
        latest_application = ScholarshipApplication.query\
            .filter_by(roll_number=student.roll_number)\
            .order_by(ScholarshipApplication.created_at.desc())\
            .first()
            
        if not latest_application:
            return False, "No active application found"

        # Get required documents based on student category and year
        required_docs = validation_service.get_required_documents(
            student_category = student.category,
            course_year=latest_application.year
        )

        # Check verification status from session
        verified_docs = session.get('verified_documents', [])
        
        # Calculate verification status
        missing_docs = [doc for doc in required_docs if doc not in verified_docs]
        
        if not missing_docs:
            return True, "All documents verified"
        else:
            return False, f"Missing documents: {', '.join(missing_docs)}"

    except Exception as e:
        print(f"Error checking document verification: {str(e)}")
        return False, "Error checking verification status"
"""


# Mark OTP as used
def mark_otp_used(email):
    try:
        OTP.query.filter_by(email=email).update({"is_used": True})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error marking OTP used: {str(e)}")


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
        msg.body = f"Your OTP is: {otp}\nValid for 5 minutes."
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
    cleanup_otps()# old otps cleanup

    try:
    # Verify OTP
        otp_record = OTP.query.filter(
            OTP.email == email,
            OTP.is_used == False,
            OTP.expires_at > datetime.now()
        ).order_by(OTP.created_at.desc()).first()


        if not otp_record or otp_record.otp != user_otp:
            return jsonify({'error': 'Invalid or expired OTP'}), 400
    
    # Create student account
        new_student = Student(
            username=temp_data['name'],
            email=email,
            password=temp_data['password'],
            roll_number=temp_data['roll_number'],
            is_verified=True
        )

        otp_record.is_used = True  # Mark OTP as used
        
        try:
            db.session.add(new_student)
            db.session.commit()
            # Clear temp session
            session.pop('temp_signup', None)

            #extra
            #session.clear()
            #session.permanent = True

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
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Failed to create account'}), 500


    except Exception as e:
        print(f"Verification error: {str(e)}")
        return jsonify({'error': 'Verification failed'}), 500


def cleanup_otps():
    """Clean up used and expired OTPs"""
    try:
        with app.app_context():
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

    data = request.get_json()
    user_id = data.get('user_id')
    password = data.get('password')
    print (f"idarrr {password} {user_id}")

    if not user_id or not password:
        return jsonify({'error': 'Missing credentials'}), 400


    #Find admin by user_id
    admin = Admin.query.filter_by(user_id=user_id).first()
    print(f"admin found: {admin}")

    if not admin:
        return jsonify({'error': 'Invalid admin ID'}), 400

    if admin.password != password:
        return jsonify({"error": "Invalid password"}), 401

    # 3. Create admin session
    session['admin_id'] = admin.user_id
    session['user_type'] = 'admin'
    session['username'] = admin.user_id
    
    
    #session.modified = True

    return jsonify({
        "message": "Login successful",
        "success": True,
        "redirect": "/admin_dashboard",
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
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))

    try:

        # Get today's appointments
        today = datetime.now().date()
        # Get today's appointments with join to get student and application details
        recent_appointments = db.session.query(
            Appointment, 
            ScholarshipApplication, Student
        ).join(
            ScholarshipApplication,
            Appointment.application_id == ScholarshipApplication.id
        ).join(
            Student,
            func.substr(Student.email, 1, func.instr('@', Student.email) - 1) == ScholarshipApplication.roll_number
        ).filter(
            Appointment.appointment_date == today
        ).order_by(Appointment.time_slot).all()

        # Count total appointments for today
        today_appointments = len(recent_appointments)


        # Count pending appointments (state is 'appointment_booked')
        pending_appointments = sum(
            1 for _, app, _ in recent_appointments 
            if app.scholarship_state == 'appointment_booked'
        )

        # Count completed appointments
        completed_appointments = sum(
            1 for _, app, _ in recent_appointments 
            if app.scholarship_state == 'completed'
        )


        # Format appointments for template
        formatted_appointments = [{
            'student_name': student.username,
            'roll_number': student.roll_number,
            'branch': application.branch,
            'year': application.year,
            'time_slot': appointment.time_slot,
            'status': application.scholarship_state,
            'application_id': application.id,
            'appointment_id': appointment.id
        } for appointment, application, student in recent_appointments]


        return render_template(
            'admin_dashboard.html',
            username=session.get('admin_id'),
            total_appointments=today_appointments,
            pending_appointments=pending_appointments,
            completed_appointments=completed_appointments,
            recent_appointments=formatted_appointments
        )

    except Exception as e:
        print(f"Error loading admin dashboard: {str(e)}")
        return redirect(url_for('admin_login'))
    
# Add new route to handle appointment completion
@app.route('/complete_appointment/<string:application_id>', methods=['POST'])
def complete_appointment(application_id):
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Update application state
        application = ScholarshipApplication.query.get_or_404(application_id)
        application.scholarship_state = 'completed'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Application marked as completed'
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error completing appointment: {str(e)}")
        return jsonify({'error': str(e)}), 500
    

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
    student = db.session.get(Student, session['user_id'])
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


# API route to get user data
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

# faculty dashboard routes
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

# circular(notifications from admins) routes
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

# route for displaying content on available teachers page
# displaying timetable for teachers
@app.route('/get_timetable/<int:teacher_id>')
def get_timetable(teacher_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    teacher = db.session.get_or_404(Teacher, teacher_id)

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

# route to get available teachers
@app.route('/available_teachers', methods=['GET'])
def available_teachers():
    """Handle both API and view requests for available teachers"""
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))
        
    try:
        # Get student's application
        student = db.session.get(Student, session['user_id'])
        # Fix: Use student's roll_number directly instead of email
        application = ScholarshipApplication.query.filter_by(
            roll_number=student.email.split('@')[0] 
        ).order_by(ScholarshipApplication.created_at.desc()).first()
        
        if not application:
            print(f"No application found for student {student.roll_number}")  # Debug log
            return redirect(url_for('fill_form'))
            
        # Debug log
        print(f"Application found: {application.id}, State: {application.scholarship_state}")
        
        # Get date parameter or use current date
        selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get unavailable teachers for selected date
        unavailable_teacher_ids = [
            t.username for t in TeacherUnavailability.query.filter_by(date=selected_date).all()
        ]
        
        # Get available teachers
        available_teachers = Teacher.query.filter(
            Teacher.username.notin_(unavailable_teacher_ids) if unavailable_teacher_ids else True
        ).all()

        # Return HTML view with application data
        return render_template('available_teachers.html',
                            teachers=available_teachers,
                            selected_date=selected_date,
                            application_type=application.lateral_entry,
                            application_year=application.year)

    except Exception as e:
        print(f"Error in available_teachers route: {str(e)}")  # Debug log
        return redirect(url_for('student_dashboard'))

# Document upload routes
@app.route('/upload_doc', methods=['GET', 'POST'])
def upload_doc():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        return render_template('upload_doc.html')
 



@app.route('/upload_doc_year1', methods=['GET', 'POST'])
def upload_doc_year1():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        # Render the upload form page
        return render_template('upload_doc_year1.html')
            

@app.route('/upload_doc_reg', methods=['GET', 'POST'])
def upload_doc_reg():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
    
    if request.method == 'GET':
        # Render the upload form page
        return render_template('upload_doc_reg.html')

      
"""
@app.route('/check_documents_status')
def check_documents_status():
    
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'verified': False, 'message': 'Unauthorized'}), 401

    verified, message = check_all_documents_verified(session['user_id'])
    return jsonify({
        'verified': verified,
        'message': message
    })
"""


#Appointment routes
@app.route('/upload_meeseva_slip', methods=['POST'])
def upload_meeseva_slip():
    file = request.files['file']
    image_data = file.read()

    # OCR processing
    details = verify_meeseva_slip_details(image_data)
    print(details)

    # Lookup app ID
    student = db.session.get(Student, session['user_id'])
    application = db.session.query(ScholarshipApplication).filter_by(
        roll_number=student.email.split('@')[0],  # Extract roll number from email
    ).order_by(ScholarshipApplication.created_at.desc()).first()
    if application:
        details["application_id"] = application.id

    return jsonify(details)


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    file = request.files.get('file')
    student = db.session.get(Student, session['user_id'])
    application = db.session.query(ScholarshipApplication).filter_by(
        roll_number=student.email.split('@')[0],  # Extract roll number from email
    ).order_by(ScholarshipApplication.created_at.desc()).first()
    application_id = application.id
    date_str = request.form.get('appointment_date')
    time_slot = request.form.get('time_slot')

    if not all([file, application_id, date_str, time_slot]):
        return jsonify({"success": False, "message": "Missing data"}), 400

    try:
        appointment = Appointment(
            application_id=application_id,
            slip_data=file.read(),
            slip_name=file.filename,
            appointment_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
            time_slot=time_slot
        )
        db.session.add(appointment)
        application = ScholarshipApplication.query.get(application_id)
        if application:
            application.scholarship_state = 'appointment_booked'

        db.session.commit()
        return jsonify({"success": True, "redirect": "/student_dashboard"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)})
    
# Route to finalize the appointment and update state
@app.route('/complete_appointment_process', methods=['POST'])
def complete_appointment_process():
    student = db.session.get(Student, session['user_id'])
    application = db.session.query(ScholarshipApplication).filter_by(
        roll_number=student.email.split('@')[0],  # Extract roll number from email
    ).order_by(ScholarshipApplication.created_at.desc()).first()
    application_id = application.id if application else None
    if not application_id:
        return jsonify({"success": False, "message": "Missing application ID"}), 400

    try:
        application = ScholarshipApplication.query.get(application_id)
        if application:
            # CORRECTED: Update to the proper state name
            application.scholarship_state = 'appointment_booked'
            db.session.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "Application not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


# Appointment page route
@app.route('/appointment', methods=['GET'])
def appointment_page():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))
    return render_template('appointment.html')



@app.route('/previous_applications')
def previous_applications():
    """Display list of previous scholarship applications for the logged-in user."""
    try:
        # Check if user is logged in and is a student
        if 'user_id' not in session or session.get('user_type') != 'student':
            return redirect(url_for('login'))

        # Get current user's email from session
        student = db.session.get(Student, session['user_id'])
        if not student:
            return redirect(url_for('login'))

        # Extract roll number from email
        roll_number = student.email.split('@')[0]

        # Query all applications for this roll number
        applications = ScholarshipApplication.query\
            .filter_by(roll_number=roll_number)\
            .order_by(ScholarshipApplication.created_at.desc())\
            .all()

        # Format application data for display
        formatted_applications = [{
            'application_id': app.id,
            'roll_number': app.roll_number,
            'branch': app.branch,
            'year': app.year,
            'status': app.scholarship_state,
            'applied_date': app.created_at.strftime('%d-%m-%Y'),
            'is_lateral_entry': app.lateral_entry
        } for app in applications]

        return render_template('previous_applications.html', 
                             applications=formatted_applications,
                             student_name=student.username)

    except Exception as e:

        return redirect(url_for('student_dashboard'))
    
@app.route('/progress')
def progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get student's application status
        student = db.session.get(Student, session['user_id'])
        application = db.session.query(ScholarshipApplication).filter_by(
            roll_number=student.email.split('@')[0],  # Extract roll number from email
        ).order_by(ScholarshipApplication.created_at.desc()).first()
        
        if not application:
            return redirect(url_for('fill_form'))
            
        # Map application states to progress steps
        current_step = 1  # Default to step 1
        

        # Determine current step based on scholarship_state
        if application.scholarship_state == 'started':
            current_step = 1  # Form submitted
            if application.lateral_entry:
                next_page = '/list_of_doc'
            else:
                if str(application.year) == '1':
                    next_page = '/list_of_doc_year1'
                else:
                    next_page = '/list_of_doc_reg'
        elif application.scholarship_state == 'documents_verified':
            current_step = 3  # Documents verified by admin
            next_page = '/appointment'  # Redirect to appointment page
        elif application.scholarship_state == 'appointment_booked':
            current_step = 4  # Biometric done and appointment booked
            next_page = None
        elif application.scholarship_state == 'completed':
            current_step = 5  # Process completed
            next_page = '/fill_form'

        # Get student category and year for context
        context = {
            'current_step': current_step,
            'student_name': student.username,
            'roll_number': student.roll_number,
            'branch': application.branch,
            'year': application.year,
            'application_id': application.id,
            'application_date': application.created_at.strftime('%d-%m-%Y'),
            'status': application.scholarship_state,
            'next_page': next_page,
            'lateral_entry': application.lateral_entry
        }
        return render_template('progress.html', **context)
        
    except Exception as e:
        print(f"Error loading progress page: {str(e)}")
        return redirect(url_for('student_dashboard'))

# logout     
@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

# Fill form route
@app.route('/fill_form')
def fill_form():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('index'))
    return render_template('fill_form.html')

# Scholarship application form submission
@app.route('/submit_scholarship_form', methods=['POST'])
def submit_scholarship_form():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        data = request.get_json()

        if not all(data.get(field) for field in ['id', 'roll_number', 'branch', 'year']):
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if application already exists
        existing_app = ScholarshipApplication.query.filter_by(
            roll_number=data['roll_number'],
            year=data['year']
        ).first()
        
        if existing_app:
            return jsonify({'error': 'Application already exists for this year'}), 400
        
        # Create new application
        application = ScholarshipApplication(
            id = data['id'],
            roll_number=data['roll_number'],
            branch=data['branch'],
            year=data['year'],
            lateral_entry=data.get('lateral_entry', False),
            scholarship_state='started'
        )
        
        db.session.add(application)
        db.session.commit()

        # Determine the next page based on student type and year
        if data.get('lateral_entry'):
            # Lateral Entry route
            next_page = '/list_of_doc'
        else:
            # Regular student route
            if str(data['year']) == '1':
                next_page = '/list_of_doc_year1'
            else:
                next_page = '/list_of_doc_reg'
        
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully',
            'redirect': next_page
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print("Error:", str(e))  # Debug log
        return jsonify({'error': str(e)}), 500

# Document list route
@app.route('/list_of_doc')
def list_of_doc():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    # Render the document list page
    return render_template('list_of_doc.html')

@app.route('/list_of_doc_year1')
def list_of_doc_year1():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    return render_template('list_of_doc_year1.html')

@app.route('/list_of_doc_reg')
def list_of_doc_reg():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('index'))

    return render_template('list_of_doc_reg.html')

# ADMIN ROUTES HERE

# displaying all applications
@app.route('/applications_list')
def applic():
    print("Session:", dict(session))
    if 'admin_id' not in session or session.get('user_type') != 'admin':
        return redirect(url_for('admin_login'))

    try:
        # Get filter parameters
        branch = request.args.get('branch', 'All Branches')
        course_year = request.args.get('year', 'All Years')
        status = request.args.get('scholarship_state', 'All Statuses')
        academic_year = request.args.get('academic_year', 'All Years')

        print(f"Applied filters - branch: {branch}, year: {course_year}, status: {status}, academic_year: {academic_year}")


        # Base query with join
        query = ScholarshipApplication.query

        # Apply filters safely
        if branch and branch != 'All Branches':
            query = query.filter(ScholarshipApplication.branch == branch)
        if status and status != 'All Statuses':
            query = query.filter(ScholarshipApplication.scholarship_state == status)
        if course_year and course_year != 'All Years' and course_year.isdigit():
            query = query.filter(ScholarshipApplication.year == course_year)
        if academic_year and academic_year != 'All Years':
            try:
                year_int = int(academic_year)
                query = query.filter(extract('year', ScholarshipApplication.created_at) == year_int)
            except ValueError:
                print(f"Invalid academic year value: {academic_year}")

        applications_data = []
        raw_applications = query.order_by(ScholarshipApplication.created_at.desc()).all()

        for application in raw_applications:
            student = Student.query.filter(Student.email.like(f"{application.roll_number}%")).first()
            if student:
                applications_data.append({
                    'id': application.id,
                    'roll_number': application.roll_number,
                    'branch': application.branch,
                    'year': application.year,
                    'scholarship_state': application.scholarship_state,
                    'created_at': application.created_at,
                    'student_name': student.username,
                    'student_email': student.email
                })

        print(f"Processed {len(applications_data)} applications with student data")


        branches = [
            'CSE', 
            'IT', 
            'ECE', 
            'EEE', 
            'Mech',
            'AIML',
            'AIDS',
            'CSE(DS)',
            'CSAI',
            'Civil'
        ]

        course_years = [1, 2, 3, 4]

        # Get academic years from created_at column
        academic_years_query = db.session.query(
            extract('year', ScholarshipApplication.created_at).label('year')
        ).filter(
            ScholarshipApplication.created_at.isnot(None)
        ).distinct()

        academic_years = sorted(set(
            int(year[0]) for year in academic_years_query.all()
            if year[0] is not None
        ), reverse=True) or [datetime.now().year]

        # Get applications with ordering
        #applications = query.order_by(ScholarshipApplication.created_at.desc()).all()

        print(f"Found {len(applications_data)} applications")  # Debug log

        return render_template(
            'applications_list.html',
            applications=applications_data,
            branches=branches, 
            years=course_years,  
            academic_years=academic_years,  # Convert to int and filter None
            statuses=['started', 'documents_verified', 'appointment_booked', 'completed'],
            current_filters={
                'branch': branch,
                'year': course_year,
                'status': status,
                'academic_year': academic_year
            }
        )

    except Exception as e:
        print(f"Error loading admin applications: {str(e)}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('admin_dashboard'))
    



# Upload documents routes

#document 10 - aadhaar card
@app.route('/upload_aadhaar', methods=['POST'])
def upload_aadhaar():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "aadhaar_valid": False}), 400

    file = request.files['file']
    image_data = file.read()
    details = extract_aadhar_details(image_data)
    return jsonify(details)

#document acknowledgement form
@app.route('/upload_ack_form', methods=['POST'])
def upload_ack_form():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = extract_ack_form_details(image_data)
    return jsonify(details)

#document application form
@app.route('/upload_application_form', methods=['POST'])
def upload_application_form():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400

    file = request.files['file']
    image_data = file.read()

    # --- Fetch the year from the ScholarshipApplication table ---
    # Example: get the latest application for the logged-in student
    student = db.session.get(Student, session['user_id'])
    application = db.session.query(ScholarshipApplication).filter_by(
        roll_number=student.email.split('@')[0],  # Extract roll number from email
    ).order_by(ScholarshipApplication.created_at.desc()).first()
    year = application.year if application else None
    lateral_entry = application.lateral_entry if application else None


    # --- Pass year to the verification function ---
    details = verify_application_form(image_data, year, lateral_entry)
    return jsonify(details)


#document previous sem memo form
@app.route('/upload_sem_memo', methods=['POST'])
def upload_sem_memo():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400

    file = request.files['file']
    image_data = file.read()

    # --- Fetch the year from the ScholarshipApplication table ---
    # Example: get the latest application for the logged-in student
    student = db.session.get(Student, session['user_id'])
    application = db.session.query(ScholarshipApplication).filter_by(
        roll_number=student.email.split('@')[0],  # Extract roll number from email
    ).order_by(ScholarshipApplication.created_at.desc()).first()
    year = application.year if application else None
    roll_number = application.roll_number if application else None


    # --- Pass year to the verification function ---
    details = verify_previous_sem_memo_details(image_data, year, roll_number)
    return jsonify(details)


#document income certificate
@app.route('/upload_income_certificate', methods=['POST'])
def upload_income_certificate():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_income_certificate_details(image_data)
    return jsonify(details)

#document original income certificate- for 1st yrs
@app.route('/upload_original_income_certificate', methods=['POST'])
def upload_original_income_certificate():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_original_income_certificate_details(image_data)
    return jsonify(details)

#document 3
@app.route('/upload_declaration_form', methods=['POST'])
def upload_declaration_form():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_declaration_form_details(image_data)
    return jsonify(details)

#document college bonafide
@app.route('/upload_present_year_bonafide', methods=['POST'])
def upload_present_year_bonafide():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_current_bonafide_details(image_data)
    return jsonify(details)

#document declaration bond certificate
@app.route('/upload_declaration_bond', methods=['POST'])
def upload_declaration_bond():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_declaration_form_details(image_data)
    return jsonify(details)


#document school bonafide
@app.route('/upload_school_bonafide', methods=['POST'])
def upload_school_bonafide():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_tenth_bonafide_details(image_data)
    return jsonify(details)

#document inter bonafide
@app.route('/upload_inter_bonafide', methods=['POST'])
def upload_inter_bonafide():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_inter_bonafide_details(image_data)
    return jsonify(details)

#document 10th memo
@app.route('/upload_tenth_memo', methods=['POST'])
def upload_tenth_memo():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_tenth_memo_details(image_data)
    return jsonify(details)

#document inter_memo
@app.route('/upload_inter_memo', methods=['POST'])
def upload_inter_memo():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_inter_memo_details(image_data)
    return jsonify(details)

#document 8
@app.route('/upload_previous_sem_memo', methods=['POST'])
def upload_previous_sem_memo():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_previous_sem_memo_details(image_data)
    return jsonify(details)

#document ration card
@app.route('/upload_ration_card', methods=['POST'])
def upload_ration_card():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_ration_card_details(image_data)
    return jsonify(details)

#document bank passbook
@app.route('/upload_bank_passbook', methods=['POST'])
def upload_bank_passbook():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_bank_passbook_details(image_data)
    return jsonify(details)


#document 13
@app.route('/upload_ou_common_service_fee', methods=['POST'])
def upload_ou_common_service_fee():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_ou_common_service_fee_details(image_data)
    return jsonify(details)

#document allotment order
@app.route('/upload_allotment_order', methods=['POST'])
def upload_allotment_order():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_allotment_order_details(image_data)
    return jsonify(details)

#document inter tc
@app.route('/upload_intermediate_tc', methods=['POST'])
def upload_intermediate_tc():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_inter_tc_details(image_data)
    return jsonify(details)

#document caste certificate
@app.route('/upload_caste_certificate', methods=['POST'])
def upload_caste_certificate():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_caste_certificate_details(image_data)
    return jsonify(details)

#document attendance form
@app.route('/upload_attendance_form', methods=['POST'])
def upload_attendance_form():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "valid": False}), 400
        
    file = request.files['file']
    image_data = file.read()
    details = verify_attendance_form_details(image_data)
    return jsonify(details)

# Mark documents as verified for a particular scholarship application
@app.route('/mark_documents_verified', methods=['POST'])
def mark_documents_verified():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    try:
        # Get the latest application for the student
        student = db.session.get(Student, session['user_id'])
        application = db.session.query(ScholarshipApplication).filter_by(
            roll_number=student.email.split('@')[0]
        ).order_by(ScholarshipApplication.created_at.desc()).first()

        if not application:
            return jsonify({'success': False, 'message': 'No application found'}), 404

        application.scholarship_state = 'documents_verified'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

from rag import PDFQuestionAnswering

# Load the PDF and keep the QA object ready (do this once at startup)
load_dotenv()
api_key = os.getenv("PDF_QA_API_KEY")
pdf_qa = PDFQuestionAnswering(api_key)
pdf_path = r"C:\Users\HOME\OneDrive\Desktop\scholarship portal\Scholarship rag.pdf"
pdf_qa.load_pdf(pdf_path)

@app.route('/api/ask', methods=['POST'])
def ask_rag():
    data = request.get_json()
    question = data.get('question', '')
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    try:
        # Get answer from RAG model
        result = pdf_qa.qa_chain.invoke({"query": question})
        answer = result.get("result", "Sorry, I couldn't find an answer.")
        return jsonify({'answer': answer})
    except Exception as e:
        print(f"RAG error: {str(e)}")
        return jsonify({'error': 'Error processing your question.'}), 500

if __name__ == '__main__':
    app.run(debug = True, port = 8000)