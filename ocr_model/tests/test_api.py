import os
import json
import pytest
from io import BytesIO
from unittest.mock import patch

def test_upload_no_document(client):
    """Test upload endpoint with no document."""
    response = client.post('/upload')
    assert response.status_code == 400
    assert b'No document part in the request' in response.data

def test_upload_no_file_selected(client):
    """Test upload endpoint with no file selected."""
    response = client.post('/upload', data={'document': (BytesIO(), '')})
    assert response.status_code == 400
    assert b'No file selected' in response.data

def test_upload_invalid_file_type(client):
    """Test upload endpoint with invalid file type."""
    response = client.post('/upload', data={
        'document': (BytesIO(b'test data'), 'test.txt')
    })
    assert response.status_code == 400
    assert b'File type not allowed' in response.data

def test_upload_invalid_document_type(client):
    """Test upload endpoint with invalid document type."""
    response = client.post('/upload', data={
        'document': (BytesIO(b'test data'), 'test.pdf'),
        'document_type': 'invalid'
    })
    assert response.status_code == 400
    assert b'Invalid document type' in response.data

@patch('worker.celery_tasks.process_document.delay')
def test_upload_valid_document(mock_process_document, client):
    """Test upload endpoint with valid document."""
    # Mock the Celery task
    mock_process_document.return_value.id = 'test_task_id'
    
    # Create a test PDF file
    pdf_data = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000057 00000 n \n0000000111 00000 n \ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF'
    
    response = client.post('/upload', data={
        'document': (BytesIO(pdf_data), 'test.pdf'),
        'document_type': 'aadhaar'
    })
    
    assert response.status_code == 202
    data = json.loads(response.data)
    assert 'document_id' in data
    assert data['task_id'] == 'test_task_id'
    assert data['status'] == 'processing'
    
    # Verify the Celery task was called
    mock_process_document.assert_called_once()

def test_result_not_found(client):
    """Test result endpoint with non-existent task ID."""
    response = client.get('/result/nonexistent_task_id')
    assert response.status_code == 404
    assert b'Task not found' in response.data

def test_result_processing(client):
    """Test result endpoint with processing task."""
    # Insert a test record directly into the database
    with client.application.app_context():
        from app.db.db import get_db
        db = get_db()
        db.execute(
            'INSERT INTO verification_results (document_id, task_id, status, feedback) VALUES (?, ?, ?, ?)',
            ('test_doc_id', 'test_task_id', 'processing', 'Document processing started')
        )
        db.commit()
    
    response = client.get('/result/test_task_id')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'processing'

def test_result_completed(client):
    """Test result endpoint with completed task."""
    # Insert a test record directly into the database
    with client.application.app_context():
        from app.db.db import get_db
        db = get_db()
        db.execute(
            'INSERT INTO verification_results (document_id, task_id, status, feedback) VALUES (?, ?, ?, ?)',
            ('test_doc_id', 'test_completed_id', 'pass', 'All required fields found')
        )
        db.commit()
    
    response = client.get('/result/test_completed_id')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'completed'
    assert data['result']['status'] == 'pass'
    assert data['result']['feedback'] == 'All required fields found'
