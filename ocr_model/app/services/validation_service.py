import re
import os
import spacy
import sqlite3
from datetime import datetime

class ValidationService:
    """Service for validating document content."""

    _nlp = None
    @staticmethod
    def get_nlp():
        if ValidationService._nlp is None:
            ValidationService._nlp = spacy.load('en_core_web_sm')
        return ValidationService._nlp

    def validate_document(self, text, document_type, student_id=None, student_category=None, gemini_info=None):
        """Validate document content based on document type with Gemini-first, OCR-fallback logic."""
        if not text and not gemini_info:
            return {'status': 'Rejected', 'feedback': 'No content to validate'}

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
            return {'status': 'Rejected', 'feedback': 'Unknown document type'}

        # Category compatibility check
        category_check = self.check_document_category_compatibility(document_type, student_category, gemini_info=gemini_info)
        if category_check['status'] == 'Rejected':
            return category_check

        # Document-specific validation
        result = validation_methods[document_type](text, student_category, gemini_info=gemini_info)
        if result['status'] == 'Rejected':
            return result

        # Consistency check if student_id provided
        if student_id:
            consistency = self.check_consistency(text, document_type, student_id, gemini_info=gemini_info)
            if consistency['status'] == 'Rejected':
                return consistency
        return result

    def validate_aadhaar(self, text, student_category=None, gemini_info=None):
        """Validate Aadhaar card content. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('aadhaar_number') or kf.get('Aadhaar Number')):
                missing.append('aadhaar number')
            if not (kf.get('dob') or kf.get('DOB')):
                missing.append('date of birth')
            if not (kf.get('gender') or kf.get('Gender')):
                missing.append('gender')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}

        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Name
        validation['has_name'] = any(ent.label_ == 'PERSON' for ent in doc.ents)
        if not validation['has_name']:
            validation['missing_fields'].append('name')
        # Aadhaar number
        if not re.search(r'\d{4}\s\d{4}\s\d{4}', text):
            validation['missing_fields'].append('aadhaar number')
        # DOB
        dob_found = any(ent.label_ == 'DATE' for ent in doc.ents)
        if not dob_found:
            if not re.search(r'(\d{2}[/-]\d{2}[/-]\d{4})', text):
                validation['missing_fields'].append('date of birth')
        # Gender
        if not re.search(r'\b(male|female|other|transgender|m|f|o|t)\b', text, re.IGNORECASE):
            validation['missing_fields'].append('gender')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_allotment_order(self, text, student_category=None, gemini_info=None):
        """Validate Allotment Order. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'allotment' in kf.get('heading', '').lower()):
                missing.append('allotment order heading')
            if not (kf.get('college_name') or kf.get('College Name')):
                missing.append('college name')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('candidate name')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if 'PROVISIONAL ALLOTMENT ORDER' not in text.upper():
            validation['missing_fields'].append('allotment order heading')
        # College name
        if not re.search(r'MJCT|M J COLLEGE|BANJARA HILLS', text, re.IGNORECASE):
            validation['missing_fields'].append('college name')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('candidate name')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_10th_marks_memo(self, text, student_category=None, gemini_info=None):
        """Validate 10th Marks Memo. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('hall_ticket') or kf.get('Hall Ticket Number')):
                missing.append('hall ticket number')
            if not (kf.get('board_name') or kf.get('Board Name')):
                missing.append('board name')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # Hall ticket
        if not re.search(r'[A-Za-z0-9]{10,11}', text):
            validation['missing_fields'].append('hall ticket number')
        # Board name
        if not re.search(r'ssc|cbse|icse|international gcse|edexcel|pearson|ib|state board', text, re.IGNORECASE):
            validation['missing_fields'].append('board name')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_intermediate_marks_memo(self, text, student_category=None, gemini_info=None):
        """Validate Intermediate Marks Memo. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'intermediate' in kf.get('heading', '').lower()):
                missing.append('intermediate marks memo heading')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('father_name') or kf.get('Father Name')):
                missing.append("father's name")
            if not (kf.get('mother_name') or kf.get('Mother Name')):
                missing.append("mother's name")
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if not re.search(r'INTERMEDIATE.*PASS.*CERTIFICATE.*MEMORANDUM.*MARKS', text, re.IGNORECASE):
            validation['missing_fields'].append('intermediate marks memo heading')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # Father's name
        if not re.search(r"father(?:'s|’s|s)? name", text, re.IGNORECASE):
            validation['missing_fields'].append("father's name")
        # Mother's name
        if not re.search(r"mother(?:'s|’s|s)? name", text, re.IGNORECASE):
            validation['missing_fields'].append("mother's name")
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_school_bonafide(self, text, student_category=None, gemini_info=None):
        """Validate School Bonafide Certificate. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'bonafide' in kf.get('heading', '').lower()):
                missing.append('bonafide certificate heading')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('school_name') or kf.get('School Name')):
                missing.append('school name')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if not re.search(r'BONAFIDE CERTIFICATE', text, re.IGNORECASE):
            validation['missing_fields'].append('bonafide certificate heading')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # School name
        if not re.search(r'school', text, re.IGNORECASE):
            validation['missing_fields'].append('school name')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_intermediate_bonafide(self, text, student_category=None, gemini_info=None):
        """Validate Intermediate Bonafide Certificate. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'bonafide' in kf.get('heading', '').lower()):
                missing.append('bonafide certificate heading')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('college_name') or kf.get('College Name')):
                missing.append('college name')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if not re.search(r'BONAFIDE CERTIFICATE', text, re.IGNORECASE):
            validation['missing_fields'].append('bonafide certificate heading')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # College name
        if not re.search(r'college', text, re.IGNORECASE):
            validation['missing_fields'].append('college name')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_intermediate_transfer_certificate(self, text, student_category=None, gemini_info=None):
        """Validate Intermediate Transfer Certificate. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'transfer certificate' in kf.get('heading', '').lower()):
                missing.append('transfer certificate heading')
            if not (kf.get('college_name') or kf.get('College Name')):
                missing.append('college name')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if not re.search(r'TRANSFER CERTIFICATE', text, re.IGNORECASE):
            validation['missing_fields'].append('transfer certificate heading')
        # College name
        if not re.search(r'college', text, re.IGNORECASE):
            validation['missing_fields'].append('college name')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_be_bonafide_certificate(self, text, student_category=None, gemini_info=None):
        """Validate BE Bonafide Certificate. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('college_name') or kf.get('College Name')):
                missing.append('college name')
            if not (kf.get('heading') and 'bonafide' in kf.get('heading', '').lower()):
                missing.append('bonafide certificate heading')
            if not (kf.get('date') or kf.get('Date')):
                missing.append('date')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        # College name
        if not re.search(r'MUFFAKHAM JAH COLLEGE|MUFFAKHAMJAH|ENGINEERING & TECHNOLOGY', text, re.IGNORECASE):
            return {'status': 'Rejected', 'feedback': 'Invalid file attached'}
        # Heading
        if not re.search(r'BONAFIDE|CONDUCT CERTIFICATE', text, re.IGNORECASE):
            return {'status': 'Rejected', 'feedback': 'Invalid file attached'}
        # Date (current year)
        if str(datetime.now().year) not in text:
            return {'status': 'Rejected', 'feedback': 'Invalid file attached'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_income_certificate(self, text, student_category=None, gemini_info=None):
        """Validate Income Certificate. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('heading') and 'income certificate' in kf.get('heading', '').lower()):
                missing.append('income certificate heading')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('application_number') or kf.get('Application Number')):
                missing.append('application number')
            if not (kf.get('date') or kf.get('Date')):
                missing.append('date')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Heading
        if not re.search(r'INCOME CERTIFICATE', text, re.IGNORECASE):
            validation['missing_fields'].append('income certificate heading')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # Application number
        if not re.search(r'[A-Za-z0-9]{14}', text):
            validation['missing_fields'].append('application number')
        # Date
        if not re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', text):
            validation['missing_fields'].append('date')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_student_bank_pass_book(self, text, student_category=None, gemini_info=None):
        """Validate Student Bank Pass Book. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('bank_name') or kf.get('Bank Name')):
                missing.append('bank name')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('account_number') or kf.get('Account Number')):
                missing.append('account number')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # Bank name
        if not re.search(r'bank', text, re.IGNORECASE):
            validation['missing_fields'].append('bank name')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # Account number
        if not re.search(r'\d{9,18}', text):
            validation['missing_fields'].append('account number')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_latest_sem_memo(self, text, student_category=None, gemini_info=None):
        """Validate Latest Sem Memo. Gemini-first, fallback to OCR."""
        if gemini_info and isinstance(gemini_info, dict):
            kf = gemini_info.get('key_fields', {})
            missing = []
            if not (kf.get('university_name') or kf.get('University Name')):
                missing.append('university name')
            if not (kf.get('examination_name') or kf.get('Examination Name')):
                missing.append('examination name')
            if not (kf.get('name') or kf.get('Name')):
                missing.append('name')
            if not (kf.get('roll_no') or kf.get('Roll No')):
                missing.append('roll no')
            if missing:
                return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(missing)})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        nlp = self.get_nlp()
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        doc = nlp(text)
        validation = {'missing_fields': []}
        # University name
        if not re.search(r'OSMANIA UNIVERSITY', text, re.IGNORECASE):
            validation['missing_fields'].append('university name')
        # Examination name
        if not re.search(r'semester|annual|examination', text, re.IGNORECASE):
            validation['missing_fields'].append('examination name')
        # Name
        if not any(ent.label_ == 'PERSON' for ent in doc.ents):
            validation['missing_fields'].append('name')
        # Roll no
        if not re.search(r'roll\s*no|rollno|roll\s*number', text, re.IGNORECASE):
            validation['missing_fields'].append('roll no')
        if validation['missing_fields']:
            return {'status': 'Rejected', 'feedback': f'Invalid file attached (missing: {", ".join(validation["missing_fields"])})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def check_consistency(self, text, document_type, student_id=None, gemini_info=None):
        """Check consistency of Name and Roll No across documents for a student. Uses Gemini structured info if available."""
        # Use Gemini info if provided
        if gemini_info and isinstance(gemini_info, dict):
            extracted_name = gemini_info.get('key_fields', {}).get('name') or gemini_info.get('key_fields', {}).get('Name')
            extracted_roll_no = gemini_info.get('key_fields', {}).get('roll_no') or gemini_info.get('key_fields', {}).get('Roll No')
        else:
            # Extract name and roll no from current document
            extracted_name = self.extract_name(text, document_type, gemini_info=gemini_info)
            extracted_roll_no = self.extract_roll_no(text, document_type, gemini_info=gemini_info)

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
                    if not self.names_match(extracted_name, reference_name, gemini_info=gemini_info):
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

    def extract_name(self, text, document_type=None, gemini_info=None):
        """Extract name from text using enhanced pattern matching. Uses Gemini info if available."""

        # Use Gemini info if provided
        if gemini_info and isinstance(gemini_info, dict):
            name = gemini_info.get('key_fields', {}).get('name') or gemini_info.get('key_fields', {}).get('Name')
            if name:
                return name.strip()

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
        nlp = self.get_nlp()
        doc = nlp(text)
        if not isinstance(text, str):
            return None
        # Find the first PERSON entity
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text.strip()

        return None

    def extract_roll_no(self, text, document_type, gemini_info=None):
        """Extract roll number from text based on document type. Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            roll_no = gemini_info.get('key_fields', {}).get('roll_no') or gemini_info.get('key_fields', {}).get('Roll No')
            if roll_no:
                return roll_no.strip()

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

    def names_match(self, name1, name2, gemini_info=None):
        """Check if two names match (allowing for minor variations). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            # If Gemini provides a match/validation, trust it
            if gemini_info.get('names_match') is not None:
                return bool(gemini_info['names_match'])

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

    def get_required_documents(self, student_category, course_year=None, gemini_info=None):
        """
        Determine required documents based on student category and course year. Uses Gemini info if available.
        """
        if gemini_info and isinstance(gemini_info, dict):
            req_docs = gemini_info.get('required_documents')
            if req_docs:
                return req_docs

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

    def check_document_category_compatibility(self, document_type, student_category, gemini_info=None):
        """
        Check if a document type is compatible with the student category. Uses Gemini info if available.
        """
        if gemini_info and isinstance(gemini_info, dict):
            compatible = gemini_info.get('category_compatible')
            if compatible is not None:
                return {'status': 'Approve' if compatible else 'Rejected', 'feedback': 'Gemini category compatibility'}

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

    def validate_scholarship_application_form(self, text, student_category=None, gemini_info=None):
        """Validate Scholarship Application Form content with category-specific rules and dynamic current year. Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            status = gemini_info.get('status')
            feedback = gemini_info.get('feedback')
            if status and feedback:
                return {'status': status, 'feedback': feedback}

        nlp = self.get_nlp()
        doc = nlp(text)

        # Get current year dynamically
        current_year = str(datetime.now().year)

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

    def validate_income_bond_paper(self, text, student_category=None, gemini_info=None):
        """Validate Income Bond Paper content (not required for 1st-year students). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_heading'):
                missing_fields.append('Income Bond Paper heading')
            if not gemini_info.get('has_name'):
                missing_fields.append('name')
            if not gemini_info.get('has_amount'):
                missing_fields.append('amount')
            if not gemini_info.get('has_signature'):
                missing_fields.append('signature')
            if missing_fields:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
            else:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}

        nlp = self.get_nlp()
        doc = nlp(text)

        # Initialize validation results
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

    def validate_scholarship_acknowledgement_form(self, text, student_category=None, gemini_info=None):
        """Validate Scholarship Acknowledgement Form content - simplified to check for 'Acknowledgement' keyword. Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_acknowledgement'):
                missing_fields.append('Acknowledgement keyword')
            if not gemini_info.get('has_name'):
                missing_fields.append('student name')
            if not gemini_info.get('has_current_year'):
                missing_fields.append('current year')
            if missing_fields:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
            else:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}

        from datetime import datetime
        import re

        nlp = self.get_nlp()
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

    def validate_attendance_sheet_form(self, text, student_category=None, gemini_info=None):
        """Validate Attendance Sheet Form. Gemini first, fallback to simple OCR date check."""
        from datetime import datetime
        current_year = str(datetime.now().year)
        if gemini_info and isinstance(gemini_info, dict):
            key_fields = gemini_info.get('key_fields', {})
            if not (key_fields.get('date') or key_fields.get('Date')):
                return {'status': 'Rejected', 'feedback': 'Invalid file attached (missing: date)'}
            # Optionally check year
            if current_year not in str(key_fields.get('date', '')):
                return {'status': 'Rejected', 'feedback': f'Date must be in current year ({current_year})'}
            return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
        # OCR fallback: just check for a date in the current year
        date_pattern = rf'\d{{2}}[/-]\d{{2}}[/-]{current_year}'
        if not re.search(date_pattern, text):
            return {'status': 'Rejected', 'feedback': f'Date must be in current year ({current_year})'}
        return {'status': 'Approve', 'feedback': 'Uploaded successfully'}

    def validate_diploma_certificate(self, text, student_category=None, gemini_info=None):
        """Validate Diploma Certificate content (for Lateral Entry students). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_diploma_heading'):
                missing_fields.append('diploma certificate heading')
            if not gemini_info.get('has_institution_name'):
                missing_fields.append('institution name')
            if not gemini_info.get('has_name'):
                missing_fields.append('student name')
            # Flexible: Pass if at least 2/3
            criteria_met = sum([
                gemini_info.get('has_diploma_heading'),
                gemini_info.get('has_institution_name'),
                gemini_info.get('has_name')
            ])
            if criteria_met >= 2:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
            else:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
        nlp = self.get_nlp()
        doc = nlp(text)
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        # Initialize validation results
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

    def validate_le_diploma_consolidated_memo(self, text, student_category=None, gemini_info=None):
        """Validate LE Diploma Consolidated Memo content (refined for Lateral Entry students). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_top_heading'):
                missing_fields.append('institutional heading')
            if not gemini_info.get('has_box_heading'):
                missing_fields.append('consolidated memorandum heading')
            if not gemini_info.get('has_name'):
                missing_fields.append('candidate name')
            # Flexible: Pass if at least 1/3
            criteria_met = sum([
                gemini_info.get('has_top_heading'),
                gemini_info.get('has_box_heading'),
                gemini_info.get('has_name')
            ])
            if criteria_met >= 1:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
            else:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
        nlp = self.get_nlp()
        doc = nlp(text)
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
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

    def validate_le_bonafide(self, text, student_category=None, gemini_info=None):
        """Validate LE Bonafide content (refined for Lateral Entry students). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_odc_number'):
                missing_fields.append('ODC Number')
            if not gemini_info.get('has_certify_name'):
                missing_fields.append('certification statement')
            if not gemini_info.get('has_top_heading'):
                missing_fields.append('institutional heading')
            if not gemini_info.get('telangana_found'):
                missing_fields.append('Telangana reference')
            if not gemini_info.get('bonafide_found'):
                missing_fields.append('bonafide/certificate keyword')
            # Flexible: Pass if at least 3/5
            criteria_met = sum([
                gemini_info.get('has_odc_number'),
                gemini_info.get('has_certify_name'),
                gemini_info.get('has_top_heading'),
                gemini_info.get('telangana_found'),
                gemini_info.get('bonafide_found')
            ])
            if criteria_met >= 3:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
            else:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
        nlp = self.get_nlp()
        doc = nlp(text)
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
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

    def validate_le_transfer_certificate(self, text, student_category=None, gemini_info=None):
        """Validate LE Transfer Certificate content (refined for Lateral Entry students). Uses Gemini info if available."""
        if gemini_info and isinstance(gemini_info, dict):
            missing_fields = []
            if not gemini_info.get('has_polytechnic_heading'):
                missing_fields.append('polytechnic/institution heading')
            if not gemini_info.get('has_transfer_certificate_heading'):
                missing_fields.append('transfer certificate heading')
            if not gemini_info.get('has_name'):
                missing_fields.append('student name')
            # Flexible: Pass if at least 1/3
            criteria_met = sum([
                gemini_info.get('has_polytechnic_heading'),
                gemini_info.get('has_transfer_certificate_heading'),
                gemini_info.get('has_name')
            ])
            if criteria_met >= 1:
                return {'status': 'Approve', 'feedback': 'Uploaded successfully (Gemini)'}
            else:
                return {'status': 'Rejected', 'feedback': f'Missing fields: {", ".join(missing_fields)} (Gemini)'}
        nlp = self.get_nlp()
        doc = nlp(text)
        if not isinstance(text, str):
            return {'status': 'Rejected', 'feedback': 'Invalid input: text must be a string'}
        validation = {'missing_fields': []}
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