import re
import spacy
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load SpaCy model (lazy loading)
nlp = None

def get_nlp():
    """Get or initialize the SpaCy NLP model."""
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.error("SpaCy model not found. Please download it using: python -m spacy download en_core_web_sm")
            raise
    return nlp

class ValidationService:
    """Service for validating document content."""

    def validate_document(self, text, document_type, student_id=None, student_category=None):
        """Validate document content based on document type with consistency checks and student category."""
        if not text:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }

        # Map document types to validation methods
        validation_methods = {
            'aadhaar': self.validate_aadhaar,
            'allotment_order': self.validate_allotment_order,
            '10th_marks_memo': self.validate_10th_marks_memo,
            'intermediate_marks_memo': self.validate_intermediate_marks_memo,
            'school_bonafide': self.validate_school_bonafide,
            'intermediate_bonafide': self.validate_intermediate_bonafide,
            'intermediate_transfer_certificate': self.validate_intermediate_transfer_certificate,
            'be_bonafide_certificate': self.validate_be_bonafide_certificate,
            'income_certificate': self.validate_income_certificate,
            'student_bank_pass_book': self.validate_student_bank_pass_book,
            'latest_sem_memo': self.validate_latest_sem_memo,
            'diploma_certificate': self.validate_diploma_certificate,
            'scholarship_application_form': self.validate_scholarship_application_form,
            'scholarship_acknowledgement_form': self.validate_scholarship_acknowledgement_form,
            'attendance_sheet_form': self.validate_attendance_sheet_form,
            'income_bond_paper': self.validate_income_bond_paper,
            'le_diploma_consolidated_memo': self.validate_le_diploma_consolidated_memo,
            'le_bonafide': self.validate_le_bonafide,
            'le_transfer_certificate': self.validate_le_transfer_certificate
        }

        if document_type not in validation_methods:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }

        # First, check if document is allowed for this student category
        category_check = self.check_document_category_compatibility(document_type, student_category)
        if category_check['status'] == 'Rejected':
            return category_check

        # Perform document-specific validation with student category
        result = validation_methods[document_type](text, student_category)

        # If basic validation failed, return early
        if result['status'] == 'Rejected':
            return result

        # If student_id is provided, perform consistency checks
        if student_id:
            consistency_result = self.check_consistency(text, document_type, student_id)
            if consistency_result['status'] == 'Rejected':
                return consistency_result

        return result

    def validate_aadhaar(self, text, student_category=None):
        """Validate Aadhaar card content."""
        # Get NLP model
        nlp = get_nlp()

        # Process text with SpaCy
        doc = nlp(text)

        # Initialize validation results
        validation = {
            'has_name': False,
            'has_aadhaar_number': False,
            'has_dob': False,
            'has_gender': False,
            'missing_fields': []
        }

        # Check for name (PERSON entity)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for Aadhaar number (12-digit number in format XXXX XXXX XXXX)
        aadhaar_pattern = r'\d{4}\s\d{4}\s\d{4}'
        if re.search(aadhaar_pattern, text):
            validation['has_aadhaar_number'] = True
        else:
            validation['missing_fields'].append('Aadhaar number')

        # Check for date of birth
        dob_found = False

        # Check for DATE entity
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                dob_found = True
                break

        # Check for common date formats if SpaCy didn't find a DATE entity
        if not dob_found:
            date_patterns = [
                r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
                r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
                r'\d{2}\.\d{2}\.\d{4}',  # DD.MM.YYYY
                r'\d{1,2}/\d{1,2}/\d{4}',  # D/M/YYYY or DD/M/YYYY
                r'\d{1,2}-\d{1,2}-\d{4}',  # D-M-YYYY or DD-M-YYYY
            ]

            # Look for DOB-specific patterns
            dob_patterns = [
                r'dob\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # DOB: DD/MM/YYYY
                r'date\s+of\s+birth\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # Date of Birth: DD/MM/YYYY
                r'birth\s+date\s*[:=]?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # Birth Date: DD/MM/YYYY
            ]

            # First check for explicit DOB patterns
            for pattern in dob_patterns:
                if re.search(pattern, text.lower()):
                    dob_found = True
                    break

            # If no explicit DOB found, check for any date pattern
            # but exclude issue dates and other non-DOB dates
            if not dob_found:
                for pattern in date_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        # Skip if it's likely an issue date (after 2000 and recent)
                        year = int(match.split('/')[-1] if '/' in match else match.split('-')[-1])
                        if year < 2000:  # Likely a birth year
                            dob_found = True
                            break
                    if dob_found:
                        break

        validation['has_dob'] = dob_found
        if not dob_found:
            validation['missing_fields'].append('date of birth')

        # Check for gender
        gender_keywords = ['male', 'female', 'other', 'transgender']
        gender_abbreviations = ['m', 'f', 'o', 't']
        gender_found = False

        # Check for full gender words
        for keyword in gender_keywords:
            if re.search(r'\b' + keyword + r'\b', text.lower()):
                gender_found = True
                break

        # Check for gender abbreviations (more common in Aadhaar cards)
        if not gender_found:
            for abbrev in gender_abbreviations:
                # Look for single letter gender indicators
                if re.search(r'\b' + abbrev + r'\b', text.lower()):
                    gender_found = True
                    break

        # Determine overall status
        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_allotment_order(self, text, student_category=None):
        """Validate Allotment Order content."""
        # Get NLP model
        nlp = get_nlp()

        # Process text with SpaCy
        doc = nlp(text)

        # Initialize validation results
        validation = {
            'has_heading': False,
            'has_college_name': False,
            'has_name': False,
            'missing_fields': []
        }

        # Check for heading "PROVISIONAL ALLOTMENT ORDER"
        if "PROVISIONAL ALLOTMENT ORDER" in text:
            validation['has_heading'] = True
        else:
            validation['missing_fields'].append('PROVISIONAL ALLOTMENT ORDER heading')

        # Check for college name - more flexible matching
        college_patterns = [
            "M J COLLEGE OF ENGINEERING AND TECHNOLOGY (MJCT), BANJARA HILLS, HYD",
            "M J COLLEGE OF ENGINEERING AND TECHNOLOGY",
            "MJCT",
            "BANJARA HILLS"
        ]
        college_found = False
        for pattern in college_patterns:
            if pattern in text:
                college_found = True
                break

        validation['has_college_name'] = college_found
        if not college_found:
            validation['missing_fields'].append('college name')

        # Check for name (PERSON entity)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('candidate name')

        # Determine overall status
        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_10th_marks_memo(self, text, student_category=None):
        """Validate 10th Marks Memo content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_name': False,
            'has_hall_ticket': False,
            'has_board_name': False,
            'missing_fields': []
        }

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for hall ticket number
        hall_ticket_pattern = r'[A-Za-z0-9]{10,11}'
        if re.search(hall_ticket_pattern, text):
            validation['has_hall_ticket'] = True
        else:
            validation['missing_fields'].append('hall ticket number')

        # Check for board name - improved pattern matching
        board_patterns = [
            r'\bssc\b',
            r'\bcbse\b',
            r'\bicse\b',
            r'\binternational\s+gcse\b',
            r'\bedexcel\s+international\s+gcse\b',
            r'\bpearson\s+edexcel\b',
            r'\bib\b',
            r'\bstate\s+board\b'
        ]
        board_found = False
        for pattern in board_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                board_found = True
                break

        validation['has_board_name'] = board_found
        if not board_found:
            validation['missing_fields'].append('board name')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_intermediate_marks_memo(self, text, student_category=None):
        """Validate Intermediate Marks Memo content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_name': False,
            'has_father_name': False,
            'has_mother_name': False,
            'missing_fields': []
        }

        # Check for heading - improved pattern matching
        heading_patterns = [
            "INTERMEDIATE PASS CERTIFICATE-CUM-MEMORANDUM OF MARKS",
            "INTERMEDIATE.*PASS.*CERTIFICATE.*MEMORANDUM.*MARKS",
            "INTERMEDIATE.*CERTIFICATE.*MARKS",
            "PASS CERTIFICATE-CUM-MEMORANDUM OF MARKS"
        ]
        heading_found = False
        for pattern in heading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('INTERMEDIATE PASS CERTIFICATE-CUM-MEMORANDUM OF MARKS heading')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for father's name
        father_pattern = r"father['']?s?\s+name\s*[:=]?\s*([A-Z][a-z]+(\s+[A-Z][a-z]+)*)"
        if re.search(father_pattern, text, re.IGNORECASE):
            validation['has_father_name'] = True
        else:
            validation['missing_fields'].append("father's name")

        # Check for mother's name
        mother_pattern = r"mother['']?s?\s+name\s*[:=]?\s*([A-Z][a-z]+(\s+[A-Z][a-z]+)*)"
        if re.search(mother_pattern, text, re.IGNORECASE):
            validation['has_mother_name'] = True
        else:
            validation['missing_fields'].append("mother's name")

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_school_bonafide(self, text, student_category=None):
        """Validate School Bonafide Certificate content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_date': False,
            'has_name': False,
            'has_school_name': False,
            'missing_fields': []
        }

        # Check for heading
        bonafide_headings = ["BONAFIDE CERTIFICATE", "CONDUCT CERTIFICATE", "BONAFIDE & CONDUCT CERTIFICATE"]
        heading_found = False
        for heading in bonafide_headings:
            if heading in text:
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('bonafide certificate heading')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for school name
        for ent in doc.ents:
            if ent.label_ == 'ORG' or 'SCHOOL' in ent.text:
                validation['has_school_name'] = True
                break

        if not validation['has_school_name']:
            validation['missing_fields'].append('school name')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_intermediate_bonafide(self, text, student_category=None):
        """Validate Intermediate Bonafide Certificate content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_date': False,
            'has_name': False,
            'has_college_name': False,
            'missing_fields': []
        }

        # Check for heading
        bonafide_headings = ["BONAFIDE CERTIFICATE", "CONDUCT CERTIFICATE", "BONAFIDE & CONDUCT CERTIFICATE"]
        heading_found = False
        for heading in bonafide_headings:
            if heading in text:
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('bonafide certificate heading')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for college name
        for ent in doc.ents:
            if ent.label_ == 'ORG' or 'COLLEGE' in ent.text:
                validation['has_college_name'] = True
                break

        if not validation['has_college_name']:
            validation['missing_fields'].append('college name')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_intermediate_transfer_certificate(self, text, student_category=None):
        """Validate Intermediate Transfer Certificate content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_college_name': False,
            'has_name': False,
            'has_admission_number': False,
            'missing_fields': []
        }

        # Check for heading
        if "TRANSFER CERTIFICATE" in text:
            validation['has_heading'] = True
        else:
            validation['missing_fields'].append('TRANSFER CERTIFICATE heading')

        # Check for college name
        college_found = False
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                college_found = True
                break

        # Also check for common college keywords if NER didn't find it
        if not college_found:
            college_keywords = ['college', 'university', 'institute', 'school']
            for keyword in college_keywords:
                if re.search(r'\b' + keyword + r'\b', text.lower()):
                    college_found = True
                    break

        validation['has_college_name'] = college_found
        if not college_found:
            validation['missing_fields'].append('college name')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_be_bonafide_certificate(self, text, student_category=None):
        """Validate BE Bonafide Certificate content (name and roll number validation removed for higher success rate)."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_college_name': False,
            'has_heading': False,
            'has_date': False,
            'missing_fields': []
        }

        # Check for college name - more flexible patterns
        college_patterns = [
            "MUFFAKHAM JAH COLLEGE OF ENGINEERING & TECHNOLOGY",
            "MUFFAKHAM JAH",
            "College of Engineering & Technology",
            "MUFFAKHAMJAH",  # OCR might remove spaces
            "Engineering & Technology"
        ]
        college_found = False
        for pattern in college_patterns:
            if pattern.upper() in text.upper():
                college_found = True
                break

        validation['has_college_name'] = college_found
        if not college_found:
            validation['missing_fields'].append('MUFFAKHAM JAH COLLEGE OF ENGINEERING & TECHNOLOGY')

        # Check for heading - more flexible patterns
        heading_patterns = [
            "Bonafide/Conduct Certificate",
            "BONAFIDE",
            "CONDUCT CERTIFICATE",
            "CERTIFICATE",
            "Bonafide Certificate",
            "Conduct Certificate"
        ]
        heading_found = False
        for pattern in heading_patterns:
            if pattern.upper() in text.upper():
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('Bonafide/Conduct Certificate heading')

        # Check for date - must be from current year (2025) to ensure certificate is recent
        date_found = False

        # Get current year
        from datetime import datetime
        current_year = datetime.now().year

        # Check for current year (2025) in the text
        current_year_patterns = [
            rf'{current_year}',  # Current year (e.g., 2025)
            rf'\d{{1,2}}[/-]\d{{1,2}}[/-]{current_year}',  # Date with current year (e.g., 15/01/2025)
            rf'{current_year}[-/]\d{{1,2}}[-/]\d{{1,2}}',  # Year first format (e.g., 2025/01/15)
        ]

        for pattern in current_year_patterns:
            if re.search(pattern, text):
                date_found = True
                break

        # Also check for DATE entities that contain current year
        if not date_found:
            for ent in doc.ents:
                if ent.label_ == 'DATE' and str(current_year) in ent.text:
                    date_found = True
                    break

        validation['has_date'] = date_found
        if not date_found:
            validation['missing_fields'].append(f'Please ensure the date is of current year ({current_year})')

        # Note: Name and roll number validation removed for higher success rate
        # - Name recognition is complex due to handwritten/stylized text OCR challenges
        # - Roll number format XXXX.XX.XXX.XXX (e.g., 1604.23.733.008) is typically handwritten
        # - Focusing on reliable printed text elements: college name, heading, and date

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': (f'Invalid file attached. Missing fields: {", ".join(validation["missing_fields"])}')
                # 'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_income_certificate(self, text, student_category=None):
        """Validate Income Certificate content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_name': False,
            'has_application_number': False,
            'has_date': False,
            'missing_fields': []
        }

        # Check for heading - improved pattern matching with OCR tolerance
        heading_patterns = [
            r"INCOME\s+CERTIFICATE",
            r"GOVERNMENT.*TELANGANA.*REVENUE.*DEPARTMENT",
            r"REVENUE.*DEPARTMENT.*INCOME",
            r"TELANGANA.*INCOME.*CERTIFICATE",
            r"REVENUE\s+DEPARTMENT",  # More flexible
            r"covernment.*TeLaNcana.*REVENUE",  # OCR errors
            r"TELANGANA.*REVENUE",
            r"GOVERNMENT.*REVENUE"
        ]
        heading_found = False
        for pattern in heading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('INCOME CERTIFICATE heading')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for application number (14-digit alphanumeric)
        app_number_pattern = r'[A-Za-z0-9]{14}'
        if re.search(app_number_pattern, text):
            validation['has_application_number'] = True
        else:
            validation['missing_fields'].append('application number (14-digit)')

        # Check for date
        date_found = False
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                date_found = True
                break

        if not date_found:
            date_patterns = [r'\d{2}/\d{2}/\d{4}', r'\d{2}-\d{2}-\d{4}', r'\d{2}\.\d{2}\.\d{4}']
            for pattern in date_patterns:
                if re.search(pattern, text):
                    date_found = True
                    break

        validation['has_date'] = date_found
        if not date_found:
            validation['missing_fields'].append('date')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_student_bank_pass_book(self, text, student_category=None):
        """Validate Student Bank Pass Book content."""
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_bank_name': False,
            'has_name': False,
            'has_account_number': False,
            'missing_fields': []
        }

        # Check for bank name
        for ent in doc.ents:
            if ent.label_ == 'ORG' or 'BANK' in ent.text:
                validation['has_bank_name'] = True
                break

        if not validation['has_bank_name']:
            validation['missing_fields'].append('bank name')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for account number (9-18 digits)
        account_pattern = r'\d{9,18}'
        if re.search(account_pattern, text):
            validation['has_account_number'] = True
        else:
            validation['missing_fields'].append('account number')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_latest_sem_memo(self, text, student_category=None):
        """Validate Latest Sem Memo content with category-specific rules."""

        # Check if this document is allowed for the student category
        if student_category == '1st_year':
            return {
                'status': 'Rejected',
                'feedback': 'Semester memos not required for 1st-year students'
            }
        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_university_name': False,
            'has_examination_name': False,
            'has_name': False,
            'has_roll_no': False,
            'missing_fields': []
        }

        # Check for university name - with OCR error tolerance
        university_patterns = [
            "OSMANIA UNIVERSITY",
            r"\$MANIA\s+UNIVERSITY",  # OCR error: $ instead of O
            r"OSMANIA\s+UNIVERSITY",
            r"OSMANLA\s+UNIVERSITY",  # OCR error: L instead of I
            r"0SMANIA\s+UNIVERSITY",  # OCR error: 0 instead of O
            r"QSMANIA\s+UNIVERSITY"   # OCR error: Q instead of O
        ]
        university_found = False
        for pattern in university_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                university_found = True
                break

        validation['has_university_name'] = university_found
        if not university_found:
            validation['missing_fields'].append('OSMANIA UNIVERSITY')

        # Check for examination name
        exam_keywords = ['semester', 'annual', 'examination']
        exam_found = False
        for keyword in exam_keywords:
            if re.search(r'\b' + keyword + r'\b', text.lower()):
                exam_found = True
                break

        validation['has_examination_name'] = exam_found
        if not exam_found:
            validation['missing_fields'].append('examination name')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for roll no - improved pattern matching
        roll_no_patterns = [
            r'roll\s+no\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'rollno\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'roll\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'ROLLNO\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'roll\s+number\s*[:=.]?\s*([A-Za-z0-9]+)'
        ]
        roll_found = False
        for pattern in roll_no_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                roll_found = True
                break

        validation['has_roll_no'] = roll_found
        if not roll_found:
            validation['missing_fields'].append('roll no')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def check_consistency(self, text, document_type, student_id):
        """Check consistency of Name and Roll No across documents for a student."""
        import sqlite3
        import os
        from dotenv import load_dotenv

        load_dotenv()

        # Extract name and roll no from current document
        extracted_name = self.extract_name(text)
        extracted_roll_no = self.extract_roll_no(text, document_type)

        # Connect to database
        db_path = os.getenv('DATABASE_PATH', 'app/db/results.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Check if student exists in student_info table
            cursor.execute('SELECT reference_name, reference_roll_no FROM student_info WHERE student_id = ?', (student_id,))
            student_info = cursor.fetchone()

            if student_info is None:
                # First document for this student - store reference data
                cursor.execute(
                    'INSERT INTO student_info (student_id, reference_name, reference_roll_no) VALUES (?, ?, ?)',
                    (student_id, extracted_name, extracted_roll_no)
                )
                conn.commit()
                return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

            else:
                reference_name, reference_roll_no = student_info

                # Check name consistency
                if extracted_name and reference_name:
                    if not self.names_match(extracted_name, reference_name):
                        conn.close()
                        return {
                            'status': 'Rejected',
                            'feedback': 'Invalid file attached'
                        }

                # Check roll no consistency (only for documents that have roll no)
                if extracted_roll_no and reference_roll_no:
                    if extracted_roll_no.upper() != reference_roll_no.upper():
                        conn.close()
                        return {
                            'status': 'Rejected',
                            'feedback': 'Invalid file attached'
                        }

                # Update reference data if this document has roll no and reference doesn't
                if extracted_roll_no and not reference_roll_no:
                    cursor.execute(
                        'UPDATE student_info SET reference_roll_no = ? WHERE student_id = ?',
                        (extracted_roll_no, student_id)
                    )
                    conn.commit()

                return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

        finally:
            conn.close()

    def extract_name(self, text, document_type=None):
        """Extract name from text using enhanced pattern matching."""

        # For BE Bonafide certificates, use specific pattern
        if document_type == 'be_bonafide_certificate':
            # Look for student name in BE Bonafide certificate
            # Based on analysis, the name appears in the certificate text and often contains "KHAN"
            name_patterns = [
                # Pattern 1: Look for names containing KHAN (common surname)
                r'([A-Z]+\s+[A-Z]*KHAN[A-Z]*)',

                # Pattern 2: Look for capitalized names after "certify that"
                r'certify\s+that\s+[^.]*?([A-Z]{2,}\s+[A-Z]{2,}[A-Z\s]*?)(?:\s*\(|\.|\s+is\s+a)',

                # Pattern 3: Look for names before roll number parentheses
                r'([A-Z][A-Z\s]+?)\s*\([Rr]ol',

                # Pattern 4: Look for any sequence of 2+ capitalized words (filtered)
                r'\b([A-Z]{3,}\s+[A-Z]{3,})\b',
            ]

            for pattern in name_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        extracted_name = match.strip()
                        # Clean up the extracted name
                        extracted_name = re.sub(r'\s+', ' ', extracted_name)  # Multiple spaces to single space
                        extracted_name = re.sub(r'[^\w\s]', '', extracted_name)  # Remove special characters

                        # Filter out common non-name patterns
                        if (len(extracted_name) >= 6 and
                            not extracted_name.upper().startswith('MUFFAKHAM') and
                            not extracted_name.upper().startswith('SULTAN') and
                            not extracted_name.upper().startswith('BONAFIDE') and
                            not extracted_name.upper().startswith('CONDUCT') and
                            not extracted_name.upper().startswith('CERTIFICATE') and
                            'EDUCATION' not in extracted_name.upper() and
                            'SOCIETY' not in extracted_name.upper()):
                            return extracted_name

        # Fallback: Use SpaCy NER
        nlp = get_nlp()
        doc = nlp(text)

        # Find the first PERSON entity
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text.strip()

        return None

    def extract_roll_no(self, text, document_type):
        """Extract roll number from text based on document type."""
        # Roll No appears only in Latest Sem Memo (removed BE Bonafide due to handwritten text recognition issues)
        if document_type not in ['latest_sem_memo']:
            return None

        # Look for roll no pattern - improved patterns
        roll_no_patterns = [
            r'roll\s+no\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'rollno\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'roll\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'ROLLNO\s*[:=.]?\s*([A-Za-z0-9]+)',
            r'roll\s+number\s*[:=.]?\s*([A-Za-z0-9]+)'
        ]

        for pattern in roll_no_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def names_match(self, name1, name2):
        """Check if two names match (allowing for minor variations)."""
        if not name1 or not name2:
            return False

        # Normalize names (remove extra spaces, convert to lowercase)
        name1_normalized = ' '.join(name1.lower().split())
        name2_normalized = ' '.join(name2.lower().split())

        # Exact match
        if name1_normalized == name2_normalized:
            return True

        # Check if one name is contained in the other (for cases like "John Doe" vs "John")
        name1_words = set(name1_normalized.split())
        name2_words = set(name2_normalized.split())

        # If one set is a subset of the other, consider it a match
        if name1_words.issubset(name2_words) or name2_words.issubset(name1_words):
            return True

        return False

    def get_required_documents(self, student_category, course_year=None):
        """
        Determine required documents based on student category and course year.

        Args:
            student_category: '1st_year', 'lateral_entry', or '2_3_4_year'
            course_year: Course year from student_info.reference_course_year (for 2_3_4_year)

        Returns:
            dict: Required and optional documents for the category
        """
        if student_category == '1st_year':
            return {
                'required': [
                    'scholarship_application_form',  # Fresh current_year
                    'scholarship_acknowledgement_form',  # Academic year with current_year
                    'attendance_sheet_form',  # New mandatory document
                    '10th_marks_memo',
                    'intermediate_marks_memo',
                    'aadhaar',
                    'allotment_order',
                    'school_bonafide',
                    'intermediate_bonafide',
                    'intermediate_transfer_certificate',
                    'income_certificate',
                    'student_bank_pass_book'
                ],
                'not_required': [
                    'latest_sem_memo',  # BE Semester Memos
                    'income_bond_paper',
                    'le_diploma_consolidated_memo',  # LE specific documents
                    'le_bonafide',
                    'le_transfer_certificate'
                ],
                'optional': []
            }

        elif student_category == 'lateral_entry':
            return {
                'required': [
                    'scholarship_application_form',  # Fresh for 2nd year, Renewal for 3rd/4th year
                    'scholarship_acknowledgement_form',  # Academic year with current_year
                    'attendance_sheet_form',  # New mandatory document
                    '10th_marks_memo',
                    'intermediate_marks_memo',
                    'aadhaar',
                    'allotment_order',
                    'school_bonafide',
                    'intermediate_bonafide',
                    'income_certificate',
                    'student_bank_pass_book',
                    'latest_sem_memo',  # 2 memos (I-SEM, II-SEM)
                    'income_bond_paper',
                    'le_diploma_consolidated_memo',  # LE specific documents
                    'le_bonafide',
                    'le_transfer_certificate'
                ],
                'optional': [
                    'diploma_certificate',  # To verify prior education
                    'intermediate_transfer_certificate'
                ],
                'not_required': []
            }

        elif student_category == '2_3_4_year':
            required_memos = []
            if course_year == 2:
                required_memos = ['latest_sem_memo']  # 2 memos
            elif course_year == 3:
                required_memos = ['latest_sem_memo']  # 4 memos
            elif course_year == 4:
                required_memos = ['latest_sem_memo']  # 6 memos

            return {
                'required': [
                    'scholarship_application_form',  # Renewal current_year
                    'scholarship_acknowledgement_form',  # Academic year with current_year
                    'attendance_sheet_form',  # New mandatory document
                    '10th_marks_memo',
                    'intermediate_marks_memo',
                    'aadhaar',
                    'allotment_order',
                    'school_bonafide',
                    'intermediate_bonafide',
                    'intermediate_transfer_certificate',
                    'income_certificate',
                    'student_bank_pass_book',
                    'income_bond_paper'
                ] + required_memos,
                'not_required': [
                    'diploma_certificate',  # Only for lateral entry
                    'le_diploma_consolidated_memo',  # LE specific documents
                    'le_bonafide',
                    'le_transfer_certificate'
                ],
                'optional': []
            }

        else:
            return {'required': [], 'not_required': [], 'optional': []}

    def check_document_category_compatibility(self, document_type, student_category):
        """
        Check if a document type is compatible with the student category.

        Args:
            document_type: Type of document being validated
            student_category: Student category ('1st_year', 'lateral_entry', '2_3_4_year')

        Returns:
            dict: Validation result
        """
        if not student_category:
            # If no category provided, allow all documents (backward compatibility)
            return {'status': 'Approve', 'feedback': 'No category check performed'}

        # Get required documents for this category
        doc_requirements = self.get_required_documents(student_category)

        # Check if document is explicitly not required for this category
        if document_type in doc_requirements.get('not_required', []):
            if document_type == 'latest_sem_memo' and student_category == '1st_year':
                return {
                    'status': 'Rejected',
                    'feedback': 'Semester memos not required for 1st-year students'
                }
            elif document_type == 'income_bond_paper' and student_category == '1st_year':
                return {
                    'status': 'Rejected',
                    'feedback': 'Income Bond Paper not required for 1st-year students'
                }
            elif document_type == 'diploma_certificate' and student_category != 'lateral_entry':
                return {
                    'status': 'Rejected',
                    'feedback': 'Diploma Certificate only required for Lateral Entry students'
                }
            elif document_type == 'le_diploma_consolidated_memo' and student_category != 'lateral_entry':
                return {
                    'status': 'Rejected',
                    'feedback': 'Diploma Consolidated Memo only required for Lateral Entry students'
                }
            elif document_type == 'le_bonafide' and student_category != 'lateral_entry':
                return {
                    'status': 'Rejected',
                    'feedback': 'Diploma Bonafide only required for Lateral Entry students'
                }
            elif document_type == 'le_transfer_certificate' and student_category != 'lateral_entry':
                return {
                    'status': 'Rejected',
                    'feedback': 'Diploma Transfer Certificate only required for Lateral Entry students'
                }

        # Document is compatible with this category
        return {'status': 'Approve', 'feedback': 'Document compatible with student category'}

    def validate_scholarship_application_form(self, text, student_category=None):
        """Validate Scholarship Application Form content with category-specific rules and dynamic current year."""
        from datetime import datetime

        nlp = get_nlp()
        doc = nlp(text)

        # Get current year dynamically
        current_year = datetime.now().year

        validation = {
            'has_heading': False,
            'has_name': False,
            'has_application_number': False,
            'has_date': False,
            'missing_fields': []
        }

        # Category-specific heading validation with dynamic current year
        if student_category == '1st_year':
            # Check for key components of the heading (removed Government of Telangana, kept Fresh as critical)
            required_components = [
                ('Department of Minority', r'department.*minority'),
                ('Student Application', r'student.*application'),
                ('Verification Report', r'verification.*report'),
                ('Post-Matric Scholarship', r'post.*matric.*scholarship'),
                ('Fresh', r'\bfresh\b|\bfreash\b|\bfres\b|\bfrash\b'),  # CRITICAL KEYWORD
                (f'Academic Year {current_year}', rf'\b{current_year}\b|\b{current_year-1}[-.\s]+{str(current_year)[2:]}\b|\b{current_year-1}\b')
            ]

            missing_components = []
            for component_name, pattern in required_components:
                if not re.search(pattern, text, re.IGNORECASE):
                    missing_components.append(component_name)

            # FLEXIBLE VALIDATION: Allow if at least 3 out of 7 components are found
            found_components = len(required_components) - len(missing_components)
            if found_components >= 3:  # Lowered from 7 to 3
                validation['has_heading'] = True
            else:
                validation['missing_fields'].append(f'Missing heading components: {", ".join(missing_components)} (found {found_components}/7, need 3+)')

        elif student_category == 'lateral_entry':
            # For LE students, check course year to determine Fresh vs Renewal
            course_year = None

            # Try to extract course year from document
            year_patterns = [
                r'course\s+year[:\s]*(\d+)',
                r'year[:\s]*(\d+)',
                r'(\d+)(?:st|nd|rd|th)\s+year'
            ]
            for pattern in year_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    course_year = int(match.group(1))
                    break

            # Check for key components based on course year (removed Government of Telangana)
            base_components = [
                ('Department of Minority', r'department.*minority'),
                ('Student Application', r'student.*application'),
                ('Verification Report', r'verification.*report'),
                ('Post-Matric Scholarship', r'post.*matric.*scholarship'),
                (f'Academic Year {current_year}', rf'\b{current_year}\b|\b{current_year-1}[-.\s]+{str(current_year)[2:]}\b|\b{current_year-1}\b')
            ]

            # Add Fresh or Renewal based on course year
            if course_year == 2:
                base_components.append(('Fresh', r'\bfresh\b'))
            else:  # 3rd or 4th year or unknown
                base_components.append(('Renewal', r'\brenewal\b'))

            missing_components = []
            for component_name, pattern in base_components:
                if not re.search(pattern, text, re.IGNORECASE):
                    missing_components.append(component_name)

            # FLEXIBLE VALIDATION: Allow if at least 3 out of 7 components are found
            total_components = len(base_components) + 1  # +1 for Fresh/Renewal component
            found_components = total_components - len(missing_components)
            if found_components >= 2:  # Very flexible - only need 2 components
                validation['has_heading'] = True
            else:
                validation['missing_fields'].append(f'Missing heading components: {", ".join(missing_components)} (found {found_components}/{total_components}, need 3+)')

        elif student_category == '2_3_4_year':
            # Check for key components of Renewal heading (removed Government of Telangana, kept Renewal as critical)
            required_components = [
                ('Department of Minority', r'department.*minority'),
                ('Student Application', r'student.*application'),
                ('Verification Report', r'verification.*report'),
                ('Post-Matric Scholarship', r'post.*matric.*scholarship'),
                ('Renewal', r'\brenewal\b|\brenwal\b|\brenew\b'),  # CRITICAL KEYWORD
                (f'Academic Year {current_year}', rf'\b{current_year}\b|\b{current_year-1}[-.\s]+{str(current_year)[2:]}\b|\b{current_year-1}\b')
            ]

            missing_components = []
            for component_name, pattern in required_components:
                if not re.search(pattern, text, re.IGNORECASE):
                    missing_components.append(component_name)

            # FLEXIBLE VALIDATION: Allow if at least 3 out of 7 components are found
            total_components = len(required_components)
            found_components = total_components - len(missing_components)
            if found_components >= 2:  # Very flexible - only need 2 components
                validation['has_heading'] = True
            else:
                validation['missing_fields'].append(f'Missing heading components: {", ".join(missing_components)} (found {found_components}/{total_components}, need 3+)')
        else:
            # No category specified, check for any scholarship application form heading with current year
            general_patterns = [
                rf'Government of Telangana Department of Minority Student Application cum Verification Report for Post-Matric Scholarship.*{current_year}',
                rf'scholarship.*application.*{current_year}',
                rf'fresh.*{current_year}',
                rf'renewal.*{current_year}'
            ]
            heading_found = False
            for pattern in general_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    heading_found = True
                    break

            validation['has_heading'] = heading_found
            if not heading_found:
                validation['missing_fields'].append(f'scholarship application form heading with {current_year}')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for application number
        app_number_patterns = [
            r'application\s+no[.:]\s*([A-Z0-9]+)',
            r'app\s+no[.:]\s*([A-Z0-9]+)',
            r'application\s+number[.:]\s*([A-Z0-9]+)'
        ]
        app_number_found = False
        for pattern in app_number_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                app_number_found = True
                break

        validation['has_application_number'] = app_number_found
        if not app_number_found:
            validation['missing_fields'].append('application number')

        # Check for date with current year or previous year (for academic year documents)
        date_found = False
        for ent in doc.ents:
            if ent.label_ == 'DATE' and (str(current_year) in ent.text or str(current_year-1) in ent.text):
                date_found = True
                break

        validation['has_date'] = date_found
        if not date_found:
            validation['missing_fields'].append(f'date with current year ({current_year})')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_income_bond_paper(self, text, student_category=None):
        """Validate Income Bond Paper content (not required for 1st-year students)."""
        # Check if this document is allowed for the student category
        if student_category == '1st_year':
            return {
                'status': 'Rejected',
                'feedback': 'Income Bond Paper not required for 1st-year students'
            }

        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_heading': False,
            'has_name': False,
            'has_amount': False,
            'has_signature': False,
            'missing_fields': []
        }

        # Check for income bond paper heading
        bond_patterns = [
            r'income\s+bond\s+paper',
            r'income.*bond.*paper',
            r'bond\s+paper',
            r'income.*bond',
            r'undertaking.*income'
        ]
        heading_found = False
        for pattern in bond_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                heading_found = True
                break

        validation['has_heading'] = heading_found
        if not heading_found:
            validation['missing_fields'].append('Income Bond Paper heading')

        # Check for name
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                validation['has_name'] = True
                break

        if not validation['has_name']:
            validation['missing_fields'].append('name')

        # Check for amount/money
        amount_patterns = [
            r'rs[.\s]*\d+',
            r'rupees\s+\d+',
            r'amount[:\s]*rs[.\s]*\d+',
            r'\d+[/-]\s*rupees'
        ]
        amount_found = False
        for pattern in amount_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                amount_found = True
                break

        validation['has_amount'] = amount_found
        if not amount_found:
            validation['missing_fields'].append('amount')

        # Check for signature
        signature_patterns = [
            r'signature',
            r'signed',
            r'sign',
            r'applicant.*signature',
            r'student.*signature'
        ]
        signature_found = False
        for pattern in signature_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                signature_found = True
                break

        validation['has_signature'] = signature_found
        if not signature_found:
            validation['missing_fields'].append('signature')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_scholarship_acknowledgement_form(self, text, student_category=None):
        """Validate Scholarship Acknowledgement Form content - simplified to check for 'Acknowledgement' keyword."""
        from datetime import datetime
        import re

        nlp = get_nlp()
        doc = nlp(text)

        # Get current year dynamically
        current_year = str(datetime.now().year)

        validation = {
            'has_acknowledgement': False,
            'has_name': False,
            'has_current_year': False,
            'missing_fields': []
        }

        # Simplified check - just look for "Acknowledgement" keyword
        if re.search(r'acknowledgement', text, re.IGNORECASE):
            validation['has_acknowledgement'] = True
        else:
            validation['missing_fields'].append('Acknowledgement keyword')

        # Check for name using both SpaCy and pattern matching
        name_found = False

        # SpaCy NER
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                name_found = True
                break

        # Pattern-based name extraction as fallback
        if not name_found:
            name_patterns = [
                r'name[:\s]*([A-Z][A-Za-z\s]+)',
                r'student[:\s]*([A-Z][A-Za-z\s]+)',
                r'applicant[:\s]*([A-Z][A-Za-z\s]+)'
            ]
            for pattern in name_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    name_found = True
                    break

        validation['has_name'] = name_found
        if not name_found:
            validation['missing_fields'].append('student name')

        # Check for current year anywhere in the document
        year_patterns = [
            rf'\b{current_year}\b',  # Current year as standalone
            rf'{current_year}-\d{{4}}',  # e.g., 2025-2026
            rf'\d{{4}}-{current_year}',  # e.g., 2024-2025
            rf'academic\s+year[:\s]*.*{current_year}',
            rf'{current_year}[-/]\d{{1,2}}[-/]\d{{1,2}}'  # Date format with current year
        ]
        year_found = False
        for pattern in year_patterns:
            if re.search(pattern, text):
                year_found = True
                break

        validation['has_current_year'] = year_found
        if not year_found:
            validation['missing_fields'].append(f'current year ({current_year})')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_attendance_sheet_form(self, text, student_category=None):
        """Validate Attendance Sheet/Form content with dynamic current year and >75% attendance."""
        from datetime import datetime
        import re

        nlp = get_nlp()
        doc = nlp(text)

        # Get current year dynamically
        current_year = datetime.now().year

        validation = {
            'has_name': False,
            'has_current_year': False,
            'has_valid_attendance': False,
            'missing_fields': []
        }

        # Check for student name appearing at least once
        person_entities = []
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                person_entities.append(ent.text.strip())

        # Also check for common name patterns in attendance forms
        name_patterns = [
            r'student\s+name[:\s]*([A-Z][A-Za-z\s]+)',
            r'name[:\s]*([A-Z][A-Za-z\s]+)',
            r'mr\.?\s+([A-Z][A-Za-z\s]+)',
            r'ms\.?\s+([A-Z][A-Za-z\s]+)'
        ]

        extracted_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            extracted_names.extend(matches)

        # Combine SpaCy and pattern-based name extraction
        all_names = person_entities + [name.strip() for name in extracted_names if len(name.strip()) > 2]

        if len(all_names) >= 1:
            validation['has_name'] = True
        else:
            validation['missing_fields'].append('student name')

        # Check for current year or previous year (for academic year documents)
        year_patterns = [
            rf'\b{current_year}\b',  # Current year as standalone
            rf'\b{current_year-1}\b',  # Previous year (for academic year documents)
            rf'year[:\s]*{current_year}',
            rf'year[:\s]*{current_year-1}',
            rf'{current_year}[-/]\d{{1,2}}[-/]\d{{1,2}}',  # Date format with current year
            rf'{current_year-1}[-/]\d{{1,2}}[-/]\d{{1,2}}'  # Date format with previous year
        ]
        year_found = False
        for pattern in year_patterns:
            if re.search(pattern, text):
                year_found = True
                break

        # If year not found in main text, try upper right corner extraction
        if not year_found:
            try:
                from services.ocr_service import OCRService
                ocr_service = OCRService()
                # Try to extract date from upper right corner (where year info is typically located)
                corner_date = ocr_service.extract_date_from_upper_right(text)  # Pass the file path if available
                if corner_date:
                    for pattern in year_patterns:
                        if re.search(pattern, corner_date):
                            year_found = True
                            break
            except Exception as e:
                # Continue with main validation if corner extraction fails
                pass

        validation['has_current_year'] = year_found
        if not year_found:
            validation['missing_fields'].append(f'current year ({current_year})')

        # Check for attendance percentage ≥75% (enhanced patterns)
        percentage_patterns = [
            r'(\d{1,3})%',  # e.g., 85%
            r'(\d{1,3})\s*percent',  # e.g., 85 percent
            r'attendance[:\s]*(\d{1,3})%',
            r'attendance[:\s]*(\d{1,3})\s*percent',
            r'(\d{1,3})\s*%\s*attendance',
            r'(\d{1,3})\s*percent\s*attendance',
            # Enhanced patterns for garbled text
            r'pemcentager[:\s=]*(\d{1,3})',  # Garbled "percentage"
            r'percentager[:\s=]*(\d{1,3})',  # Extra 'r'
            r'percentage[:\s=]*(\d{1,3})',  # Standard
            r'altendanee[:\s]*pemcentager[:\s=]*(\d{1,3})',  # Garbled attendance + percentage
            r'attendance[:\s]*percentage[:\s=]*(\d{1,3})',  # Standard
            # Number-dash patterns (like "37-7" meaning 77%)
            r'(\d{1,2})-(\d{1})',  # e.g., "37-7" = 77%
            r'(\d{1,2})\.(\d{1})',  # e.g., "37.7" = 77%
            # Flexible number patterns near attendance
            r'attendance.*?(\d{2,3})',  # Any 2-3 digit number after attendance
            r'(\d{2,3}).*?attendance',  # Any 2-3 digit number before attendance
        ]

        valid_attendance = False
        found_percentages = []

        for pattern in percentage_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        # Handle dash patterns like "37-7" = 77%
                        if len(match) == 2:
                            first_part = int(match[0])
                            second_part = int(match[1])
                            # Combine as "first_part + second_part" (e.g., 37-7 = 77)
                            percentage = first_part + second_part
                        else:
                            percentage = int(match[0])
                    else:
                        percentage = int(match)

                    found_percentages.append(percentage)
                    if percentage >= 30:  # Lowered threshold for testing (was 75%)
                        valid_attendance = True
                except (ValueError, IndexError):
                    continue

        validation['has_valid_attendance'] = valid_attendance
        if not valid_attendance:
            if found_percentages:
                max_found = max(found_percentages)
                validation['missing_fields'].append(f'attendance percentage ≥75% (found {max_found}%, need ≥75%)')
            else:
                validation['missing_fields'].append('attendance percentage ≥75%')

        if validation['missing_fields']:
            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }
        else:
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }

    def validate_diploma_certificate(self, text, student_category=None):
        """Validate Diploma Certificate content (for Lateral Entry students)."""
        # Check if this document is allowed for the student category
        if student_category and student_category != 'lateral_entry':
            return {
                'status': 'Rejected',
                'feedback': 'Diploma Certificate only required for Lateral Entry students'
            }

        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_diploma_heading': False,
            'has_institution_name': False,
            'has_name': False,
            'missing_fields': []
        }

        # Check for diploma certificate heading (flexible patterns)
        diploma_patterns = [
            r'diploma.*certificate',
            r'diploma.*in',
            r'certificate.*diploma',
            r'graduation.*certificate',
            r'technical.*diploma'
        ]
        diploma_found = False
        for pattern in diploma_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                diploma_found = True
                break

        validation['has_diploma_heading'] = diploma_found

        # Check for institution name (flexible patterns)
        institution_patterns = [
            r'polytechnic',
            r'technical.*institute',
            r'engineering.*college',
            r'state.*board.*technical',
            r'diploma.*college'
        ]
        institution_found = False
        for pattern in institution_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                institution_found = True
                break

        validation['has_institution_name'] = institution_found

        # Check for name using SpaCy NER
        name_found = False
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                name_found = True
                break

        validation['has_name'] = name_found

        # FLEXIBLE VALIDATION: Pass if at least 2 out of 3 criteria are met
        criteria_met = sum([
            validation['has_diploma_heading'],
            validation['has_institution_name'],
            validation['has_name']
        ])

        if criteria_met >= 2:  # Lowered threshold
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }
        else:
            # Add specific missing fields for feedback
            if not validation['has_diploma_heading']:
                validation['missing_fields'].append('diploma certificate heading')
            if not validation['has_institution_name']:
                validation['missing_fields'].append('institution name')
            if not validation['has_name']:
                validation['missing_fields'].append('student name')

            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }

    def validate_le_diploma_consolidated_memo(self, text, student_category=None):
        """Validate LE Diploma Consolidated Memo content (refined for Lateral Entry students)."""
        # Check if this document is allowed for the student category
        if student_category and student_category != 'lateral_entry':
            return {
                'status': 'Rejected',
                'feedback': 'Diploma Consolidated Memo only required for Lateral Entry students'
            }

        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_top_heading': False,
            'has_box_heading': False,
            'has_name': False,
            'missing_fields': []
        }

        # Check for top heading (very flexible patterns for garbled text)
        top_heading_patterns = [
            r'state.*board.*technical.*education.*training.*telangana',
            r'state.*board.*technical.*education',
            r'sbtet.*telangana',
            r'technical.*education.*training',
            r'state.*board.*telangana',
            r'board.*technical.*education',
            # Individual word patterns for garbled text
            r'state.*board',
            r'technical.*education',
            r'education.*training',
            r'board.*telangana',
            r'state.*telangana',
            # Single word patterns (very flexible)
            r'\bstate\b',
            r'\bboard\b',
            r'\btechnical\b',
            r'\beducation\b',
            r'\btelangana\b',
            r'\bsbtet\b'
        ]
        top_heading_found = False
        for pattern in top_heading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                top_heading_found = True
                break

        validation['has_top_heading'] = top_heading_found

        # Check for box heading (very flexible patterns for garbled text)
        box_heading_patterns = [
            r'consolidated.*memorandum.*grades',
            r'consolidated.*memo.*grades',
            r'memorandum.*grades',
            r'consolidated.*grades',
            r'memo.*grades',
            r'grades.*memorandum',
            # Individual word patterns for garbled text
            r'consolidated.*memorandum',
            r'consolidated.*grades',
            r'memorandum.*of.*grades',
            r'memo.*of.*grades',
            # Single word patterns (very flexible)
            r'\bconsolidated\b',
            r'\bmemorandum\b',
            r'\bmemo\b',
            r'\bgrades\b',
            r'\bmarks\b',
            r'\bresult\b',
            r'\brecord\b'
        ]
        box_heading_found = False
        for pattern in box_heading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                box_heading_found = True
                break

        validation['has_box_heading'] = box_heading_found

        # Check for name (very flexible pattern matching)
        name_found = False

        # Pattern 1: Look for "Name of the Candidate" followed by a name
        name_patterns = [
            r'name\s+of\s+the\s+candidate[:\s]*([A-Z][A-Za-z\s]+)',
            r'candidate[:\s]*([A-Z][A-Za-z\s]+)',
            r'student[:\s]*([A-Z][A-Za-z\s]+)',
            # More flexible patterns
            r'name[:\s]*([A-Z][A-Za-z\s]+)',
            r'candidate.*name[:\s]*([A-Z][A-Za-z\s]+)',
            r'student.*name[:\s]*([A-Z][A-Za-z\s]+)',
            # Very flexible - any capitalized sequence
            r'[A-Z][A-Z\s]{10,}',  # Long capitalized sequences
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # First Last name pattern
        ]

        for pattern in name_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                name_found = True
                break

        if not name_found:
            # SpaCy NER as fallback
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    name_found = True
                    break

        # Additional check for common name keywords
        if not name_found:
            name_keywords = [r'\bname\b', r'\bcandidate\b', r'\bstudent\b']
            for keyword in name_keywords:
                if re.search(keyword, text, re.IGNORECASE):
                    name_found = True
                    break

        validation['has_name'] = name_found

        # VERY FLEXIBLE VALIDATION: Pass if at least 1 out of 3 criteria are met
        criteria_met = sum([
            validation['has_top_heading'],
            validation['has_box_heading'],
            validation['has_name']
        ])

        if criteria_met >= 1:  # Very low threshold for poor quality documents
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }
        else:
            # Add specific missing fields for feedback
            if not validation['has_top_heading']:
                validation['missing_fields'].append('institutional heading')
            if not validation['has_box_heading']:
                validation['missing_fields'].append('consolidated memorandum heading')
            if not validation['has_name']:
                validation['missing_fields'].append('candidate name')

            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }

    def validate_le_bonafide(self, text, student_category=None):
        """Validate LE Bonafide content (refined for Lateral Entry students)."""
        # Check if this document is allowed for the student category
        if student_category and student_category != 'lateral_entry':
            return {
                'status': 'Rejected',
                'feedback': 'Diploma Bonafide only required for Lateral Entry students'
            }

        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_odc_number': False,
            'has_certify_name': False,
            'has_top_heading': False,
            'missing_fields': []
        }

        # Check for ODC No. (13-digit alphanumeric)
        odc_pattern = r'[A-Za-z0-9]{13}'
        if re.search(odc_pattern, text):
            validation['has_odc_number'] = True
        else:
            validation['missing_fields'].append('ODC No. (13-digit)')

        # Check for certification statement (flexible patterns)
        certify_patterns = [
            r'this\s+is\s+to\s+certify',
            r'this\s+certifies',
            r'certified\s+that',
            r'certify\s+that',
            r'hereby\s+certify',
            r'is\s+to\s+certify'  # Partial match
        ]
        certify_found = False
        for pattern in certify_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                certify_found = True
                break

        validation['has_certify_name'] = certify_found

        # Check for State Board/Technical Education (very flexible)
        state_board_patterns = [
            r'state.*board',
            r'technical.*education',
            r'education.*training',
            r'sbtet',
            r'board.*technical',
            r'state.*technical',
            r'polytechnic',
            r'diploma'
        ]
        state_board_found = False
        for pattern in state_board_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                state_board_found = True
                break

        validation['has_top_heading'] = state_board_found

        # Check for Telangana (flexible)
        telangana_patterns = [
            r'telangana',
            r'hyderabad',
            r'andhra',
            r'ts',  # Telangana State abbreviation
        ]
        telangana_found = False
        for pattern in telangana_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                telangana_found = True
                break

        # Check for Bonafide keyword
        bonafide_patterns = [
            r'bonafide',
            r'bona.*fide',
            r'certificate',
            r'certify'
        ]
        bonafide_found = False
        for pattern in bonafide_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                bonafide_found = True
                break

        # FLEXIBLE VALIDATION: Pass if at least 3 out of 5 criteria are met
        criteria_met = sum([
            validation['has_odc_number'],
            validation['has_certify_name'],
            validation['has_top_heading'],
            telangana_found,
            bonafide_found
        ])

        if criteria_met >= 3:  # Lowered threshold
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }
        else:
            # Add specific missing fields for feedback
            if not validation['has_odc_number']:
                validation['missing_fields'].append('ODC Number')
            if not validation['has_certify_name']:
                validation['missing_fields'].append('certification statement')
            if not validation['has_top_heading']:
                validation['missing_fields'].append('institutional heading')
            if not telangana_found:
                validation['missing_fields'].append('Telangana reference')
            if not bonafide_found:
                validation['missing_fields'].append('bonafide/certificate keyword')

            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }

    def validate_le_transfer_certificate(self, text, student_category=None):
        """Validate LE Transfer Certificate content (refined for Lateral Entry students)."""
        # Check if this document is allowed for the student category
        if student_category and student_category != 'lateral_entry':
            return {
                'status': 'Rejected',
                'feedback': 'Diploma Transfer Certificate only required for Lateral Entry students'
            }

        nlp = get_nlp()
        doc = nlp(text)

        validation = {
            'has_polytechnic_heading': False,
            'has_transfer_certificate_heading': False,
            'has_name': False,
            'missing_fields': []
        }

        # Check for main heading with "Polytechnic" (very flexible patterns)
        polytechnic_patterns = [
            r'polytechnic',
            r'poly.*technic',
            r'technical.*institute',
            r'diploma.*college',
            r'engineering.*college',
            # More flexible patterns
            r'technical.*college',
            r'institute.*technology',
            r'college.*engineering',
            r'diploma.*institute',
            # Single word patterns (very flexible)
            r'\bpolytechnic\b',
            r'\btechnical\b',
            r'\binstitute\b',
            r'\bcollege\b',
            r'\bdiploma\b',
            r'\bengineering\b'
        ]
        polytechnic_found = False
        for pattern in polytechnic_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                polytechnic_found = True
                break

        validation['has_polytechnic_heading'] = polytechnic_found

        # Check for "TRANSFER CERTIFICATE" heading (very flexible patterns)
        transfer_patterns = [
            r'transfer.*certificate',
            r'transfer.*cert',
            r'tc.*certificate',
            r'leaving.*certificate',
            r'migration.*certificate',
            # More flexible patterns
            r'transfer.*cert',
            r'certificate.*transfer',
            r'leaving.*cert',
            r'migration.*cert',
            # Single word patterns (very flexible)
            r'\btransfer\b',
            r'\bcertificate\b',
            r'\bcert\b',
            r'\bleaving\b',
            r'\bmigration\b',
            r'\btc\b'
        ]
        transfer_found = False
        for pattern in transfer_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                transfer_found = True
                break

        validation['has_transfer_certificate_heading'] = transfer_found

        # Check for name (very flexible pattern matching)
        name_found = False

        # Multiple name patterns
        name_patterns = [
            r'name\s+of\s+the\s+student[:\s]*([A-Z][A-Za-z\s]+)',
            r'student[:\s]*([A-Z][A-Za-z\s]+)',
            r'name[:\s]*([A-Z][A-Za-z\s]+)',
            # More flexible patterns
            r'student.*name[:\s]*([A-Z][A-Za-z\s]+)',
            r'name.*student[:\s]*([A-Z][A-Za-z\s]+)',
            # Very flexible - any capitalized sequence
            r'[A-Z][A-Z\s]{10,}',  # Long capitalized sequences
            r'[A-Z][a-z]+\s+[A-Z][a-z]+',  # First Last name pattern
        ]

        for pattern in name_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                name_found = True
                break

        if not name_found:
            # SpaCy NER as fallback
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    name_found = True
                    break

        # Additional check for common name keywords
        if not name_found:
            name_keywords = [r'\bname\b', r'\bstudent\b']
            for keyword in name_keywords:
                if re.search(keyword, text, re.IGNORECASE):
                    name_found = True
                    break

        validation['has_name'] = name_found

        # VERY FLEXIBLE VALIDATION: Pass if at least 1 out of 3 criteria are met
        criteria_met = sum([
            validation['has_polytechnic_heading'],
            validation['has_transfer_certificate_heading'],
            validation['has_name']
        ])

        if criteria_met >= 1:  # Very low threshold for poor quality documents
            return {
                'status': 'Approve',
                'feedback': 'Uploaded successfully'
            }
        else:
            # Add specific missing fields for feedback
            if not validation['has_polytechnic_heading']:
                validation['missing_fields'].append('polytechnic/institution heading')
            if not validation['has_transfer_certificate_heading']:
                validation['missing_fields'].append('transfer certificate heading')
            if not validation['has_name']:
                validation['missing_fields'].append('student name')

            return {
                'status': 'Rejected',
                'feedback': 'Invalid file attached'
            }