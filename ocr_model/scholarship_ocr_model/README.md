# Scholarship OCR Model

A Flask-based OCR service for automating document verification for a scholarship portal.

## Project Overview

This project provides a REST API for:
- Uploading documents (Aadhaar Card, Allotment Order)
- Processing documents using OCR and NLP
- Validating document content against specific rules
- Storing and retrieving validation results

## System Dependencies

Before running the application, ensure you have the following system dependencies installed:

### Tesseract OCR

#### Windows
```
choco install tesseract
```
Or download from: https://github.com/UB-Mannheim/tesseract/wiki

#### macOS
```
brew install tesseract
```

#### Linux
```
sudo apt-get install tesseract-ocr
```

### Poppler Utilities (for PDF processing)

#### Windows
```
choco install poppler
```

#### macOS
```
brew install poppler
```

#### Linux
```
sudo apt-get install poppler-utils
```

### Redis (for Celery)

#### Windows
Use Docker:
```
docker run -d -p 6379:6379 redis
```

#### macOS
```
brew install redis
brew services start redis
```

#### Linux
```
sudo apt-get install redis-server
sudo systemctl start redis
```

## Setup Instructions

1. Clone the repository
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

   **Enhanced Preprocessing Dependencies**: The project now includes advanced image preprocessing capabilities using:
   - `opencv-python`: For advanced image processing like deskewing and morphological operations
   - `numpy`: For image array operations with OpenCV
   - `scikit-image`: For image quality metrics and advanced thresholding

   Install these additional dependencies:
   ```
   pip install opencv-python numpy scikit-image
   ```

3. Download SpaCy model:
   ```
   python -m spacy download en_core_web_sm
   ```
4. Initialize the database:
   ```
   python app/db/setup.py
   ```
5. Start the Flask application:
   ```
   flask run
   ```
6. Start the Celery worker (in a separate terminal):
   ```
   celery -A worker.celery_tasks worker --loglevel=info
   ```

## API Documentation

### Upload Document
- **Endpoint**: POST /upload
- **Request**: Multipart form with file field 'document'
- **Response**: JSON with document_id and task_id

### Get Result
- **Endpoint**: GET /result/<task_id>
- **Response**: JSON with status and validation result

## Testing

Run tests using pytest:
```
pytest
```

## Project Structure

- `/app`: Main Flask application
  - `/routes`: API route definitions
  - `/services`: OCR and NLP processing logic
  - `/utils`: Helper functions
  - `/static/uploads`: Directory for storing uploaded documents
  - `/db`: SQLite database file and schema setup
- `/worker`: Celery worker for asynchronous document processing
- `/tests`: Unit tests
