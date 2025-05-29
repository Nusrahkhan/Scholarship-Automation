import os
import sqlite3
import logging
from celery import Celery
from dotenv import load_dotenv
from app.services.ocr_service import OCRService
from app.services.validation_service import ValidationService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
celery = Celery('scholarship_ocr', broker=redis_url, backend=redis_url)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery.task(bind=True)
def process_document(self, student_id, document_id, file_path, document_type, student_category=None):
    """
    Process document with OCR and validate content.

    Args:
        student_id: Student identifier for consistency checks
        document_id: Unique identifier for the document
        file_path: Path to the document file
        document_type: Type of document (e.g., 'aadhaar', 'allotment_order', etc.)
        student_category: Student category ('1st_year', 'lateral_entry', '2_3_4_year')

    Returns:
        dict: Validation result
    """
    try:
        logger.info(f"Processing document: {document_id}, student: {student_id}, type: {document_type}, category: {student_category}")

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
            # Validate document content with student category
            result = validation_service.validate_document(text, document_type, student_id, student_category)

        # Update result in database
        db_path = os.getenv('DATABASE_PATH', 'app/db/results.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE verification_results SET status = ?, feedback = ? WHERE document_id = ?',
            (result['status'], result['feedback'], document_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Document processing completed: {document_id}, status: {result['status']}")

        return result

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")

        # Update database with error
        try:
            db_path = os.getenv('DATABASE_PATH', 'app/db/results.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute(
                'UPDATE verification_results SET status = ?, feedback = ? WHERE document_id = ?',
                ('fail', f'Error processing document: {str(e)}', document_id)
            )

            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Error updating database: {str(db_error)}")

        # Re-raise exception to mark task as failed
        raise
