import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.services.validation_service import ValidationService

@pytest.fixture
def mock_nlp():
    """Mock SpaCy NLP model."""
    with patch('app.services.validation_service.get_nlp') as mock_get_nlp:
        # Create a mock NLP model
        mock_model = MagicMock()
        mock_get_nlp.return_value = mock_model
        yield mock_model

@pytest.fixture
def validation_service():
    """Create ValidationService instance."""
    return ValidationService()

@pytest.fixture
def current_year():
    """Get current year for dynamic testing."""
    return str(datetime.now().year)

def test_validate_document_no_text(validation_service):
    """Test validation with no text."""
    result = validation_service.validate_document(None, 'aadhaar')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_validate_document_unsupported_type(validation_service):
    """Test validation with unsupported document type."""
    result = validation_service.validate_document('Some text', 'unsupported')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== SCHOLARSHIP APPLICATION FORM TESTS =====

def test_scholarship_application_form_1st_year_valid(mock_nlp, validation_service, current_year):
    """Test Scholarship Application Form validation for 1st year students with valid data."""
    # Mock SpaCy entities
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'
    mock_date = MagicMock()
    mock_date.label_ = 'DATE'
    mock_date.text = f'15/01/{current_year}'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person, mock_date]
    mock_nlp.return_value = mock_doc

    text = f"""
    Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship Fresh {current_year}

    Name: John Doe
    Application No: APP123456
    Date: 15/01/{current_year}
    """

    result = validation_service.validate_scholarship_application_form(text, '1st_year')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_scholarship_application_form_1st_year_wrong_year(mock_nlp, validation_service):
    """Test Scholarship Application Form validation for 1st year with wrong year."""
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    text = """
    Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship Fresh 2024

    Name: John Doe
    Application No: APP123456
    """

    result = validation_service.validate_scholarship_application_form(text, '1st_year')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_scholarship_application_form_lateral_entry_2nd_year(mock_nlp, validation_service, current_year):
    """Test Scholarship Application Form validation for 2nd year LE students (Fresh)."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'
    mock_date = MagicMock()
    mock_date.label_ = 'DATE'
    mock_date.text = f'15/01/{current_year}'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person, mock_date]
    mock_nlp.return_value = mock_doc

    text = f"""
    Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship Fresh {current_year}

    Name: John Doe
    Application No: APP123456
    Date: 15/01/{current_year}
    Course Year: 2nd year
    """

    result = validation_service.validate_scholarship_application_form(text, 'lateral_entry')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_scholarship_application_form_lateral_entry_3rd_year(mock_nlp, validation_service, current_year):
    """Test Scholarship Application Form validation for 3rd year LE students (Renewal)."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'
    mock_date = MagicMock()
    mock_date.label_ = 'DATE'
    mock_date.text = f'15/01/{current_year}'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person, mock_date]
    mock_nlp.return_value = mock_doc

    text = f"""
    Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship Renewal {current_year}

    Name: John Doe
    Application No: APP123456
    Date: 15/01/{current_year}
    Course Year: 3rd year
    """

    result = validation_service.validate_scholarship_application_form(text, 'lateral_entry')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_scholarship_application_form_2_3_4_year_valid(mock_nlp, validation_service, current_year):
    """Test Scholarship Application Form validation for 2nd/3rd/4th year students."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'
    mock_date = MagicMock()
    mock_date.label_ = 'DATE'
    mock_date.text = f'15/01/{current_year}'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person, mock_date]
    mock_nlp.return_value = mock_doc

    text = f"""
    Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship Renewal {current_year}

    Name: John Doe
    Application No: APP123456
    Date: 15/01/{current_year}
    """

    result = validation_service.validate_scholarship_application_form(text, '2_3_4_year')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

# ===== SCHOLARSHIP ACKNOWLEDGEMENT FORM TESTS =====

def test_scholarship_acknowledgement_form_valid(mock_nlp, validation_service, current_year):
    """Test Scholarship Acknowledgement Form validation with valid data."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = f"""
    Scholarship Acknowledgement Form

    Name: John Doe
    Academic Year: {current_year}-{int(current_year)+1}
    """

    result = validation_service.validate_scholarship_acknowledgement_form(text)

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_scholarship_acknowledgement_form_wrong_year(mock_nlp, validation_service):
    """Test Scholarship Acknowledgement Form validation with wrong academic year."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    Scholarship Acknowledgement Form

    Name: John Doe
    Academic Year: 2023-2024
    """

    result = validation_service.validate_scholarship_acknowledgement_form(text)

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_scholarship_acknowledgement_form_missing_name(mock_nlp, validation_service, current_year):
    """Test Scholarship Acknowledgement Form validation with missing name."""
    mock_doc = MagicMock()
    mock_doc.ents = []  # No PERSON entities
    mock_nlp.return_value = mock_doc

    text = f"""
    Scholarship Acknowledgement Form

    Academic Year: {current_year}-{int(current_year)+1}
    """

    result = validation_service.validate_scholarship_acknowledgement_form(text)

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== ATTENDANCE SHEET/FORM TESTS =====

def test_attendance_sheet_form_valid_all_categories(mock_nlp, validation_service, current_year):
    """Test Attendance Sheet/Form validation with valid data for all categories."""
    # Mock two PERSON entities (name appearing twice)
    mock_person1 = MagicMock()
    mock_person1.label_ = 'PERSON'
    mock_person1.text = 'John Doe'
    mock_person2 = MagicMock()
    mock_person2.label_ = 'PERSON'
    mock_person2.text = 'John Doe'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person1, mock_person2]
    mock_nlp.return_value = mock_doc

    text = f"""
    Attendance Sheet

    Student Name: John Doe
    Year: {current_year}
    Attendance: 85%

    Signature: John Doe
    """

    # Test for all student categories
    for category in ['1st_year', 'lateral_entry', '2_3_4_year']:
        result = validation_service.validate_attendance_sheet_form(text, category)
        assert result['status'] == 'Approve'
        assert result['feedback'] == 'Uploaded successfully'

def test_attendance_sheet_form_wrong_year(mock_nlp, validation_service):
    """Test Attendance Sheet/Form validation with wrong year."""
    mock_person1 = MagicMock()
    mock_person1.label_ = 'PERSON'
    mock_person1.text = 'John Doe'
    mock_person2 = MagicMock()
    mock_person2.label_ = 'PERSON'
    mock_person2.text = 'John Doe'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person1, mock_person2]
    mock_nlp.return_value = mock_doc

    text = """
    Attendance Sheet

    Student Name: John Doe
    Year: 2023
    Attendance: 85%

    Signature: John Doe
    """

    result = validation_service.validate_attendance_sheet_form(text)

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_attendance_sheet_form_name_not_twice(mock_nlp, validation_service, current_year):
    """Test Attendance Sheet/Form validation with name not appearing twice."""
    # Mock only one PERSON entity
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'
    mock_person.text = 'John Doe'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = f"""
    Attendance Sheet

    Student Name: John Doe
    Year: {current_year}
    Attendance: 85%
    """

    result = validation_service.validate_attendance_sheet_form(text)

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_attendance_sheet_form_missing_percentage(mock_nlp, validation_service, current_year):
    """Test Attendance Sheet/Form validation with missing attendance percentage."""
    mock_person1 = MagicMock()
    mock_person1.label_ = 'PERSON'
    mock_person1.text = 'John Doe'
    mock_person2 = MagicMock()
    mock_person2.label_ = 'PERSON'
    mock_person2.text = 'John Doe'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person1, mock_person2]
    mock_nlp.return_value = mock_doc

    text = f"""
    Attendance Sheet

    Student Name: John Doe
    Year: {current_year}

    Signature: John Doe
    """

    result = validation_service.validate_attendance_sheet_form(text)

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== LE DIPLOMA CONSOLIDATED MEMO TESTS =====

def test_le_diploma_consolidated_memo_valid(mock_nlp, validation_service):
    """Test LE Diploma Consolidated Memo validation with valid data."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    STATE BOARD OF TECHNICAL EDUCATION AND TRAINING TELANGANA

    CONSOLIDATED MEMORANDUM OF GRADES

    Name of the Candidate: John Doe
    Roll Number: 12345
    """

    result = validation_service.validate_le_diploma_consolidated_memo(text, 'lateral_entry')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_le_diploma_consolidated_memo_wrong_category(validation_service):
    """Test LE Diploma Consolidated Memo validation for non-LE students."""
    text = """
    STATE BOARD OF TECHNICAL EDUCATION AND TRAINING TELANGANA

    CONSOLIDATED MEMORANDUM OF GRADES

    Name of the Candidate: John Doe
    """

    result = validation_service.validate_le_diploma_consolidated_memo(text, '1st_year')

    assert result['status'] == 'Rejected'
    assert 'Diploma Consolidated Memo only required for Lateral Entry students' in result['feedback']

def test_le_diploma_consolidated_memo_missing_headings(mock_nlp, validation_service):
    """Test LE Diploma Consolidated Memo validation with missing headings."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    Some other heading

    Name of the Candidate: John Doe
    """

    result = validation_service.validate_le_diploma_consolidated_memo(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_le_diploma_consolidated_memo_missing_name(mock_nlp, validation_service):
    """Test LE Diploma Consolidated Memo validation with missing name."""
    mock_doc = MagicMock()
    mock_doc.ents = []  # No PERSON entities
    mock_nlp.return_value = mock_doc

    text = """
    STATE BOARD OF TECHNICAL EDUCATION AND TRAINING TELANGANA

    CONSOLIDATED MEMORANDUM OF GRADES

    Roll Number: 12345
    """

    result = validation_service.validate_le_diploma_consolidated_memo(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== LE BONAFIDE TESTS =====

def test_le_bonafide_valid(mock_nlp, validation_service):
    """Test LE Bonafide validation with valid data."""
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    text = """
    State Board of Technical Education and Training

    ODC No: ABC1234567890

    This is to certify that John Doe is a student of this institution.
    """

    result = validation_service.validate_le_bonafide(text, 'lateral_entry')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_le_bonafide_wrong_category(validation_service):
    """Test LE Bonafide validation for non-LE students."""
    text = """
    State Board of Technical Education and Training

    ODC No: ABC1234567890

    This is to certify that John Doe is a student.
    """

    result = validation_service.validate_le_bonafide(text, '1st_year')

    assert result['status'] == 'Rejected'
    assert 'Diploma Bonafide only required for Lateral Entry students' in result['feedback']

def test_le_bonafide_missing_odc(mock_nlp, validation_service):
    """Test LE Bonafide validation with missing ODC number."""
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    text = """
    State Board of Technical Education and Training

    This is to certify that John Doe is a student.
    """

    result = validation_service.validate_le_bonafide(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_le_bonafide_missing_certify_pattern(mock_nlp, validation_service):
    """Test LE Bonafide validation with missing 'This is to certify that' pattern."""
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    text = """
    State Board of Technical Education and Training

    ODC No: ABC1234567890

    John Doe is a student of this institution.
    """

    result = validation_service.validate_le_bonafide(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_le_bonafide_missing_top_heading(mock_nlp, validation_service):
    """Test LE Bonafide validation with missing top heading."""
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp.return_value = mock_doc

    text = """
    Some other heading

    ODC No: ABC1234567890

    This is to certify that John Doe is a student.
    """

    result = validation_service.validate_le_bonafide(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== LE TRANSFER CERTIFICATE TESTS =====

def test_le_transfer_certificate_valid(mock_nlp, validation_service):
    """Test LE Transfer Certificate validation with valid data."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    Government Polytechnic College

    TRANSFER CERTIFICATE

    Name of the Student: John Doe
    Father's Name: James Doe
    """

    result = validation_service.validate_le_transfer_certificate(text, 'lateral_entry')

    assert result['status'] == 'Approve'
    assert result['feedback'] == 'Uploaded successfully'

def test_le_transfer_certificate_wrong_category(validation_service):
    """Test LE Transfer Certificate validation for non-LE students."""
    text = """
    Government Polytechnic College

    TRANSFER CERTIFICATE

    Name of the Student: John Doe
    """

    result = validation_service.validate_le_transfer_certificate(text, '1st_year')

    assert result['status'] == 'Rejected'
    assert 'Diploma Transfer Certificate only required for Lateral Entry students' in result['feedback']

def test_le_transfer_certificate_missing_polytechnic(mock_nlp, validation_service):
    """Test LE Transfer Certificate validation with missing 'Polytechnic' in heading."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    Government College

    TRANSFER CERTIFICATE

    Name of the Student: John Doe
    """

    result = validation_service.validate_le_transfer_certificate(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_le_transfer_certificate_missing_transfer_heading(mock_nlp, validation_service):
    """Test LE Transfer Certificate validation with missing 'TRANSFER CERTIFICATE' heading."""
    mock_person = MagicMock()
    mock_person.label_ = 'PERSON'

    mock_doc = MagicMock()
    mock_doc.ents = [mock_person]
    mock_nlp.return_value = mock_doc

    text = """
    Government Polytechnic College

    CERTIFICATE

    Name of the Student: John Doe
    """

    result = validation_service.validate_le_transfer_certificate(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

def test_le_transfer_certificate_missing_name(mock_nlp, validation_service):
    """Test LE Transfer Certificate validation with missing name."""
    mock_doc = MagicMock()
    mock_doc.ents = []  # No PERSON entities
    mock_nlp.return_value = mock_doc

    text = """
    Government Polytechnic College

    TRANSFER CERTIFICATE

    Father's Name: James Doe
    """

    result = validation_service.validate_le_transfer_certificate(text, 'lateral_entry')

    assert result['status'] == 'Rejected'
    assert 'Invalid file attached' in result['feedback']

# ===== CATEGORY COMPATIBILITY TESTS =====

def test_document_category_compatibility_1st_year(validation_service):
    """Test document category compatibility for 1st year students."""
    # Test that LE documents are rejected for 1st year students
    le_documents = ['le_diploma_consolidated_memo', 'le_bonafide', 'le_transfer_certificate']

    for doc_type in le_documents:
        result = validation_service.check_document_category_compatibility(doc_type, '1st_year')
        assert result['status'] == 'Rejected'
        assert 'only required for Lateral Entry students' in result['feedback']

def test_document_category_compatibility_lateral_entry(validation_service):
    """Test document category compatibility for lateral entry students."""
    # Test that LE documents are approved for lateral entry students
    le_documents = ['le_diploma_consolidated_memo', 'le_bonafide', 'le_transfer_certificate']

    for doc_type in le_documents:
        result = validation_service.check_document_category_compatibility(doc_type, 'lateral_entry')
        assert result['status'] == 'Approve'

def test_document_category_compatibility_2_3_4_year(validation_service):
    """Test document category compatibility for 2nd/3rd/4th year students."""
    # Test that LE documents are rejected for 2_3_4_year students
    le_documents = ['le_diploma_consolidated_memo', 'le_bonafide', 'le_transfer_certificate']

    for doc_type in le_documents:
        result = validation_service.check_document_category_compatibility(doc_type, '2_3_4_year')
        assert result['status'] == 'Rejected'
        assert 'only required for Lateral Entry students' in result['feedback']

def test_attendance_sheet_mandatory_all_categories(validation_service):
    """Test that attendance sheet is mandatory for all categories."""
    categories = ['1st_year', 'lateral_entry', '2_3_4_year']

    for category in categories:
        required_docs = validation_service.get_required_documents(category)
        assert 'attendance_sheet_form' in required_docs['required']

def test_scholarship_acknowledgement_mandatory_all_categories(validation_service):
    """Test that scholarship acknowledgement form is mandatory for all categories."""
    categories = ['1st_year', 'lateral_entry', '2_3_4_year']

    for category in categories:
        required_docs = validation_service.get_required_documents(category)
        assert 'scholarship_acknowledgement_form' in required_docs['required']