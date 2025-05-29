import os
import uuid
from flask import request, current_app
from flask_restful import Resource
from werkzeug.utils import secure_filename
from app.db.db import get_db

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tif', 'tiff'}

# Allowed document types
ALLOWED_DOCUMENT_TYPES = {
    'aadhaar', 'allotment_order', '10th_marks_memo', 'intermediate_marks_memo',
    'school_bonafide', 'intermediate_bonafide', 'intermediate_transfer_certificate',
    'be_bonafide_certificate', 'income_certificate', 'student_bank_pass_book',
    'latest_sem_memo', 'diploma_certificate', 'scholarship_application_form',
    'scholarship_acknowledgement_form', 'attendance_sheet_form', 'income_bond_paper',
    'le_diploma_consolidated_memo', 'le_bonafide', 'le_transfer_certificate'
}

# Allowed student categories
ALLOWED_STUDENT_CATEGORIES = {'1st_year', 'lateral_entry', '2_3_4_year'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class DocumentUpload(Resource):
    def post(self):
        """Handle document upload and trigger OCR processing."""
        # Check if file is in request
        if 'document' not in request.files:
            return {'error': 'No document part in the request'}, 400

        file = request.files['document']

        # Check if file is selected
        if file.filename == '':
            return {'error': 'No file selected'}, 400

        # Check if file has allowed extension
        if not allowed_file(file.filename):
            return {'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}, 400

        # Generate unique document ID
        document_id = str(uuid.uuid4())

        # Secure filename and save file
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{document_id}.{file_extension}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)

        # Ensure upload directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save file
        file.save(file_path)

        # Get required parameters from request
        document_type = request.form.get('document_type')
        student_id = request.form.get('student_id')
        student_category = request.form.get('student_category')

        # Validate required parameters
        if not document_type:
            return {'error': 'document_type parameter is required'}, 400

        if not student_id:
            return {'error': 'student_id parameter is required'}, 400

        if not student_category:
            return {'error': 'student_category parameter is required'}, 400

        if document_type not in ALLOWED_DOCUMENT_TYPES:
            return {
                'error': f'Invalid document type. Must be one of: {", ".join(sorted(ALLOWED_DOCUMENT_TYPES))}'
            }, 400

        if student_category not in ALLOWED_STUDENT_CATEGORIES:
            return {
                'error': f'Invalid student category. Must be one of: {", ".join(sorted(ALLOWED_STUDENT_CATEGORIES))}'
            }, 400

        # Process document synchronously for now
        # TODO: Switch back to async processing once Celery is working properly
        try:
            from app.services.ocr_service import OCRService
            from app.services.validation_service import ValidationService
            import os

            # Initialize services
            ocr_service = OCRService(tesseract_path=os.getenv('TESSERACT_PATH'))
            validation_service = ValidationService()

            # Extract text from document
            text = ocr_service.extract_text_from_file(file_path)

            if not text:
                result = {
                    'status': 'fail',
                    'feedback': 'Failed to extract text from document'
                }
            else:
                # Validate document content with consistency checks and student category
                result = validation_service.validate_document(text, document_type, student_id, student_category)

            # Generate a task ID for consistency
            task_id = str(uuid.uuid4())

            # Store result in database
            db = get_db()
            db.execute(
                'INSERT INTO verification_results (student_id, document_id, task_id, document_type, student_category, status, feedback) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (student_id, document_id, task_id, document_type, student_category, result['status'], result['feedback'])
            )
            db.commit()

            return {
                'document_id': document_id,
                'task_id': task_id,
                'status': 'completed',
                'result': result
            }, 200

        except Exception as e:
            # If processing fails, store error in database
            task_id = str(uuid.uuid4())
            error_message = f'Error processing document: {str(e)}'

            db = get_db()
            db.execute(
                'INSERT INTO verification_results (student_id, document_id, task_id, document_type, student_category, status, feedback) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (student_id, document_id, task_id, document_type, student_category, 'fail', error_message)
            )
            db.commit()

            return {
                'document_id': document_id,
                'task_id': task_id,
                'status': 'completed',
                'result': {
                    'status': 'fail',
                    'feedback': error_message
                }
            }, 200

class DocumentResult(Resource):
    def get(self, task_id):
        """Get the result of document processing."""
        db = get_db()
        result = db.execute(
            'SELECT * FROM verification_results WHERE task_id = ?',
            (task_id,)
        ).fetchone()

        if result is None:
            return {'error': 'Task not found'}, 404

        # Convert datetime to string for JSON serialization
        created_at = result['created_at']
        if created_at:
            created_at = str(created_at)

        return {
            'status': 'processing' if result['status'] == 'processing' else 'completed',
            'result': {
                'student_id': result['student_id'],
                'document_id': result['document_id'],
                'document_type': result['document_type'],
                'status': result['status'],
                'feedback': result['feedback'],
                'created_at': created_at
            }
        }

def init_app(api):
    """Initialize API routes."""
    api.add_resource(DocumentUpload, '/upload')
    api.add_resource(DocumentResult, '/result/<string:task_id>')
