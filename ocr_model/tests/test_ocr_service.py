import os
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from app.services.ocr_service import OCRService

@pytest.fixture
def test_image():
    """Create a test image for OCR testing."""
    # Create a simple test image
    img = Image.new('RGB', (200, 100), color='white')
    img_path = os.path.join(os.path.dirname(__file__), 'test_image.png')
    img.save(img_path)
    
    yield img_path
    
    # Clean up
    if os.path.exists(img_path):
        os.remove(img_path)

@patch('pytesseract.image_to_string')
def test_extract_text_from_image(mock_image_to_string, test_image):
    """Test extracting text from an image."""
    # Mock the OCR result
    mock_image_to_string.return_value = 'Test OCR Result'
    
    # Initialize OCR service
    ocr_service = OCRService()
    
    # Extract text from test image
    result = ocr_service._extract_text_from_image(test_image)
    
    # Verify the result
    assert result == 'Test OCR Result'
    assert mock_image_to_string.called

@patch('app.utils.pdf_utils.convert_pdf_to_images')
@patch('app.services.ocr_service.OCRService._extract_text_from_image')
def test_extract_text_from_pdf(mock_extract_from_image, mock_convert_pdf, test_image):
    """Test extracting text from a PDF."""
    # Mock the PDF conversion
    mock_convert_pdf.return_value = [test_image, test_image]
    
    # Mock the image extraction
    mock_extract_from_image.side_effect = ['Page 1 text', 'Page 2 text']
    
    # Initialize OCR service
    ocr_service = OCRService()
    
    # Extract text from test PDF
    result = ocr_service._extract_text_from_pdf('test.pdf')
    
    # Verify the result
    assert result == 'Page 1 text\n\nPage 2 text'
    assert mock_convert_pdf.called
    assert mock_extract_from_image.call_count == 2

def test_extract_text_from_file_unsupported_format():
    """Test extracting text from an unsupported file format."""
    # Initialize OCR service
    ocr_service = OCRService()
    
    # Extract text from unsupported file
    result = ocr_service.extract_text_from_file('test.txt')
    
    # Verify the result
    assert result is None

@patch('app.services.ocr_service.OCRService._extract_text_from_image')
def test_extract_text_from_file_image(mock_extract_from_image, test_image):
    """Test extracting text from an image file."""
    # Mock the image extraction
    mock_extract_from_image.return_value = 'Image text'
    
    # Initialize OCR service
    ocr_service = OCRService()
    
    # Extract text from image file
    result = ocr_service.extract_text_from_file(test_image)
    
    # Verify the result
    assert result == 'Image text'
    assert mock_extract_from_image.called

@patch('app.services.ocr_service.OCRService._extract_text_from_pdf')
def test_extract_text_from_file_pdf(mock_extract_from_pdf):
    """Test extracting text from a PDF file."""
    # Mock the PDF extraction
    mock_extract_from_pdf.return_value = 'PDF text'
    
    # Initialize OCR service
    ocr_service = OCRService()
    
    # Extract text from PDF file
    result = ocr_service.extract_text_from_file('test.pdf')
    
    # Verify the result
    assert result == 'PDF text'
    assert mock_extract_from_pdf.called
