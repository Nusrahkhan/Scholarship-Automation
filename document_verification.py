from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import json
import google.generativeai as genai
from datetime import datetime
import os


# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Aadhaar detail extraction
def extract_aadhar_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Indian Aadhaar card, extract the following details:
    - Name of the cardholder
    - Aadhaar Number (12 digits)
    - Date of Birth (in DD/MM/YYYY or YYYY format)

    Return the result in this exact JSON format:
    {
      "name": "",
      "aadhaar_number": "",
      "dob": ""
    }

    If any detail is not found, leave it as an empty string.
    """
    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)

        result_text = response.text
        print(result_text)

        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)

        aadhaar_clean = result.get("aadhaar_number", "").replace(" ", "")
        result["aadhaar_valid"] = len(aadhaar_clean) == 12 and aadhaar_clean.isdigit()
    except Exception as e:
        result = {
            "name": "",
            "aadhaar_number": "",
            "dob": "",
            "aadhaar_valid": False,
            "error": str(e)
        }

    return result

# Add to document_verification.py
def extract_ack_form_details(image_data):
    current_year = datetime.now().year
    expected_academic_year = f"{current_year-1}-{current_year}"
    
    prompt = f"""
    You are an intelligent OCR system. Given an image of a Scholarship Acknowledgement Form:
    1. Extract these details:
        - Application Number
        - Applicant Name
        - Academic Year
        - Institute Name
    2. Verify these critical elements:
        - Institute name must be 'Muffakkham Jah College of Engineering and Technology'
        - Presence of the word 'Acknowledgement' (case-insensitive)
        - Academic year must be {expected_academic_year}
    
    Return JSON with validation flags:
    {{
      "valid_institute": false,
      "has_acknowledgement": false,
      "valid_academic_year": false,
      "valid": false
    }}
    """

    try:
        image = Image.open(io.BytesIO(image_data))
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_institute", False) and
            result.get("has_acknowledgement", False) and
            result.get("valid_academic_year", False)
        )
        return result
        
    except Exception as e:
        return {
        "valid_institute": False,
        "has_acknowledgement": False,
        "valid_academic_year": False,
        "valid": False,
        "error": str(e),
        }
    

#document 2.1 - Income Certificate
def verify_income_certificate_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Income Certificate:
    1. Extract these details:
        - Applicant Name
        - Application Number
        - Annual Income
        - Date
    2. Verify these critical elements:
        - Presence of a heading containing 'INCOME CERTIFICATE' (case-insensitive)
        - Presence of an application number (14-digit alphanumeric starting with 'IC')
        - Presence of annual income (less than 2 lakh, written in both number and spelled format)
        - Presence of a name
        - Presence of a date
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "application_number": "",
        "annual_income": "",
        "date": ""
      },
      "valid_heading": false,
      "valid_application_number": false,
      "valid_annual_income": false,
      "has_name": false,
      "has_date": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        print(result)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("valid_application_number", False) and
            result.get("valid_annual_income", False) and
            result.get("has_name", False) and
            result.get("has_date", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "application_number": "",
                "annual_income": "",
                "date": ""
            },
            "valid_heading": False,
            "valid_application_number": False,
            "valid_annual_income": False,
            "has_name": False,
            "has_date": False,
            "valid": False,
            "error": str(e)
        }

#document 2.2 Original Income (for 1st yrs)
def verify_original_income_certificate_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Income Certificate:
    1. Extract these details:
        - Applicant Name
        - Application Number
        - Annual Income
        - Date
    2. Verify these critical elements:
        - Presence of a heading containing 'INCOME CERTIFICATE' (case-insensitive)
        - Presence of an application number (14-digit alphanumeric starting with 'IC')
        - Presence of annual income (less than 2 lakh, written in both number and spelled format)
        - Presence of a name
        - Presence of a date
        - Image must be in color (not grayscale or black-and-white)
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "application_number": "",
        "annual_income": "",
        "date": ""
      },
      "valid_heading": false,
      "valid_application_number": false,
      "valid_annual_income": false,
      "has_name": false,
      "has_date": false,
      "is_color_image": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        print(result)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("valid_application_number", False) and
            result.get("valid_annual_income", False) and
            result.get("has_name", False) and
            result.get("has_date", False) and
            result.get("is_color_image", False)
        )
        
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "application_number": "",
                "annual_income": "",
                "date": ""
            },
            "valid_heading": False,
            "valid_application_number": False,
            "valid_annual_income": False,
            "has_name": False,
            "has_date": False,
            "is_color_image": False,
            "valid": False,
            "error": str(e)
        }
    
#document 3 - Income Declaration Form
def verify_declaration_form_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Income Declaration Form:
    1. Extract these details:
        - Applicant Name
        - Total Family Annual Income
    2. Verify these critical elements:
        - Presence of a heading containing 'INCOME DECLARATION FORM' (case-insensitive)
        - Presence of a side heading containing 'Name & Signature of the Student' (case-insensitive)
        - Presence of total family annual income
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "total_family_income": ""
      },
      "valid_heading": false,
      "has_name_signature_heading": false,
      "has_total_income": false,
      "valid": false
    }
    """

    try:
        image = Image.open(io.BytesIO(image_data))
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name_signature_heading", False) and
            result.get("has_total_income", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "total_family_income": ""
            },
            "valid_heading": False,
            "has_name_signature_heading": False,
            "has_total_income": False,
            "valid": False,
            "error": str(e)
        }

#document 4 - Current Bonafide
from datetime import datetime
import io
import json
from PIL import Image

def verify_current_bonafide_details(image_data):
    current_year = datetime.now().year
    prompt = f"""
    You are an intelligent OCR system. Given an image of a BE Bonafide Certificate:
    1. Extract these details:
        - Applicant Name
        - Roll Number
        - College Name
    2. Verify these critical elements:
        - Presence of a heading containing 'BONAFIDE CERTIFICATE' or 'BE BONAFIDE CERTIFICATE' (case-insensitive)
        - Presence of a name
        - College name must be 'MUFFAKHAM JAH COLLEGE OF ENGINEERING & TECHNOLOGY' (case-insensitive)
        - Presence of a roll number
    
    Return JSON with extracted details and validation flags:
    {{
      "extracted": {{
        "name": "",
        "roll_number": "",
        "college_name": ""
      }},
      "valid_heading": false,
      "has_name": false,
      "valid_college_name": false,
      "has_roll_number": false,
      "valid": false
    }}
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Optionally, handle PDF here (extract first page as image, etc.)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
            except Exception as pdf_e:
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        print(result)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("valid_college_name", False) and
            result.get("has_roll_number", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "roll_number": "",
                "college_name": "",
                "date": ""
            },
            "valid_heading": False,
            "has_name": False,
            "valid_college_name": False,
            "valid_date": False,
            "has_roll_number": False,
            "valid": False,
            "error": str(e)
        }

#document 5.1 - Inter Bonafides
def verify_inter_bonafide_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Intermediate Bonafide Certificate:
    1. Extract these details:
        - Applicant Name
        - College Name or College Code
        - Date
    2. Verify these critical elements:
        - Presence of a heading containing 'BONAFIDE CERTIFICATE', 'INTERMEDIATE BONAFIDE CERTIFICATE', 'BONAFIDE & CONDUCT CERTIFICATE', or 'CONDUCT CERTIFICATE' (case-insensitive)
        - Presence of a name
        - Presence of a college name or college code
        - Presence of a date
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "college_name_or_code": "",
        "date": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_college_name_or_code": false,
      "has_date": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_college_name_or_code", False) and
            result.get("has_date", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "college_name_or_code": "",
                "date": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_college_name_or_code": False,
            "has_date": False,
            "valid": False,
            "error": str(e)
        }
    
#document 5.2 - School Bonafide
def verify_tenth_bonafide_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of a 10th Bonafide Certificate:
    1. Extract these details:
        - Applicant Name
        - Institution Name or School Name
    2. Verify these critical elements:
        - Presence of a heading containing 'BONAFIDE CERTIFICATE', '10TH BONAFIDE CERTIFICATE', 'BONOFIDE & CONDUCT CERTIFICATE', or 'CONDUCT CERTIFICATE' (case-insensitive)
        - Presence of a name
        - Presence of an institution name or school name
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "institution_name": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_institution_name": false,
      "valid": false
    }
    """

    try:

        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Optionally, handle PDF here (extract first page as image, etc.)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
            except Exception as pdf_e:
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_institution_name", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "institution_name": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_institution_name": False,
            "valid": False,
            "error": str(e)
        }

import mimetypes
from pdf2image import convert_from_bytes


#document 6 - Tenth Memo
def verify_tenth_memo_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of a 10th Marks Memorandum:
    1. Extract these details:
        - Applicant Name
        - Roll Number
        - Date
        - Board or Examination Name
    2. Verify these critical elements:
        - Presence of a heading containing 'MEMORANDUM OF MARKS', '10TH CLASS MEMORANDUM OF MARKS', '10TH MEMO', or 'edexcel', or 'SECONDARY SCHOOL CERTIFICATE' (case-insensitive)
        - Presence of a name
        - Presence of a roll number (with forms like 'Roll no.', 'Roll number', or 'UCI')
        - Presence of a date
        - Presence of a board or examination name (e.g., 'SSC', 'CBSE', 'GCSE', 'ICSE', 'Board of Secondary Education')
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "roll_number": "",
        "date": "",
        "board": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_roll_number": false,
      "has_date": false,
      "has_board": false,
      "valid": false
    }
    """

    try:
        # Detect file type (very basic check)
        #file_type = mimetypes.guess_type("dummy.pdf")[0]  # Replace with actual filename if available

        # Try to open as image
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Optionally, handle PDF here (extract first page as image, etc.)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
            except Exception as pdf_e:
                raise pdf_e
  
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_roll_number", False) and
            result.get("has_date", False) and
            result.get("has_board", False)
        )
        
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "roll_number": "",
                "date": "",
                "board": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_roll_number": False,
            "has_date": False,
            "has_board": False,
            "valid": False,
            "error": str(e)
        }

#document 7 - Inter Memo
def verify_inter_memo_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Intermediate Marks Memorandum:
    1. Extract these details:
        - Applicant Name
        - Roll Number
        - Board Name
    2. Verify these critical elements:
        - Presence of a heading containing 'INTERMEDIATE PASS CERTIFICATE-CUM-MEMORANDUM OF MARKS', 'MEMORANDUM OF MARKS', or 'INTER MEMO' (case-insensitive)
        - Presence of a name
        - Presence of a roll number
        - Presence of a board name (e.g., 'TELENGANA STATE BOARD OF INTERMEDIATE EDUCATION')
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "roll_number": "",
        "board": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_roll_number": false,
      "has_board": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Optionally, handle PDF here (extract first page as image, etc.)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
            except Exception as pdf_e:
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_roll_number", False) and
            result.get("has_board", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "roll_number": "",
                "board": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_roll_number": False,
            "has_board": False,
            "valid": False,
            "error": str(e)
        }

#document 8 - Previous Semester Memo
def verify_previous_sem_memo_details(image_data, year, roll_number):
    """
    Verifies the Previous Semester Memo based on year, roll_number, and required keywords.
    - If year == 2: must contain '1-sem' or '2-sem' (or roman numerals 'I-sem', 'II-sem')
    - If year == 3: must contain '3-sem' or '4-sem' (or roman numerals 'III-sem', 'IV-sem')
    - If year == 4: must contain '5-sem' or '6-sem' (or roman numerals 'V-sem', 'VI-sem')
    - Must contain the roll_number
    - Must contain: 'SEMESTER GRADE RECORD', 'OSMANIA UNIVERSITY', 'BE', 'CSE'
    """
    # Map year to valid semester numbers and roman numerals
    sem_map = {
        2: ['1', '2', 'I', 'II'],
        3: ['3', '4', 'III', 'IV'],
        4: ['5', '6', 'V', 'VI']
    }
    valid_sems = sem_map.get(int(year), [])

    prompt = f"""
    You are an intelligent OCR system. Given an image of a Previous Semester Memo, extract and validate the following:
    1. Must contain the student's roll number: {roll_number}
    2. Must contain the words: 'SEMESTER GRADE RECORD', 'OSMANIA UNIVERSITY', 'BE', 'CSE'
    3. For year {year}, must contain one of these semester indicators: {', '.join([s + '-sem' for s in valid_sems])}
    4. Extract these details:
        - Roll Number
        - Semester (as written)
        - All detected keywords from point 2
    Return JSON in this format:
    {{
      "extracted": {{
        "roll_number": "",
        "semester": "",
        "keywords_found": []
      }},
      "has_roll_number": false,
      "has_valid_semester": false,
      "has_semester_grade_record": false,
      "has_osmania_university": false,
      "has_be": false,
      "has_cse": false,
      "valid": false
    }}
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
            except Exception as pdf_e:
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("has_roll_number", False) and
            result.get("has_valid_semester", False) and
            result.get("has_semester_grade_record", False) and
            result.get("has_osmania_university", False) and
            result.get("has_be", False) and
            result.get("has_cse", False)
        )
        return result
        
    except Exception as e:
        return {
            "has_roll_number": False,
            "has_valid_semester": False,
            "has_semester_grade_record": False,
            "has_osmania_university": False,
            "has_be": False,
            "has_cse": False,
            "valid": False,
            "error": str(e),
        }

#document 9 - Ration Card
def verify_ration_card_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of a Ration Card:
    1. Extract these details:
        - Applicant Name
        - Ration Card Number or Application Number or Meeseva Application Number or Meeseva Number
    2. Verify these critical elements:
        - Presence of a heading containing 'RATION CARD', 'RATION CARD DETAILS', or 'RATION CARD MEMBER DETAILS' (case-insensitive)
        - Presence of a name
        - Presence of a ration card number, application number, Meeseva application number, or Meeseva number
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "number": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_number": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_number", False)
        )

        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "number": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_number": False,
            "valid": False,
            "error": str(e)
        }

#document 11 - Bank Passbook
def verify_bank_passbook_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of a Bank Passbook:
    1. Extract these details:
        - Account Holder's Name
        - Account Number
        - IFSC Code
    2. Verify these critical elements:
        - Presence of an account holder's name
        - Presence of an account number
        - Presence of an IFSC code
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "account_holder_name": "",
        "account_number": "",
        "ifsc_code": ""
      },
      "has_account_holder_name": false,
      "has_account_number": false,
      "has_ifsc_code": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("has_account_holder_name", False) and
            result.get("has_account_number", False) and
            result.get("has_ifsc_code", False)
        )
        
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "account_holder_name": "",
                "account_number": "",
                "ifsc_code": ""
            },
            "has_account_holder_name": False,
            "has_account_number": False,
            "has_ifsc_code": False,
            "valid": False,
            "error": str(e)
        }

#document 12 - Allotment Order
def verify_allotment_order_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Allotment Order:
    1. Extract these details:
        - Name
        - Hall Ticket Number
        - Rank
    2. Verify these critical elements:
        - Presence of a heading containing 'PROVISIONAL ALLOTMENT ORDER' (case-insensitive)
        - Presence of a name
        - Presence of a hall ticket number
        - Presence of a rank
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "hall_ticket_number": "",
        "rank": ""
      },
      "valid_heading": false,
      "has_name": false,
      "has_hall_ticket_number": false,
      "has_rank": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name", False) and
            result.get("has_hall_ticket_number", False) and
            result.get("has_rank", False)
        )
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "hall_ticket_number": "",
                "rank": ""
            },
            "valid_heading": False,
            "has_name": False,
            "has_hall_ticket_number": False,
            "has_rank": False,
            "valid": False,
            "error": str(e)
        }


#document 13 - OU Common Service Fee
def verify_ou_common_service_fee_details(image_data):
    current_year = datetime.now().year
    prompt = """
    You are an intelligent OCR system. Given an image of an OU Common Services Fee document:
    1. Extract these details:
        - Student Name
        - Date
    2. Verify these critical elements:
        - Presence of a heading containing 'Sultan-ul-uloom Education Society (M.J. College of Engg. & Tech.)' (case-insensitive)
        - Presence of the text 'Student's Copy' at the top (case-insensitive)
        - Presence of the text '6. Common Services Fee of O.U. 2500/-'
        - Presence of a date, which must be from the year {current_year}
        - Presence of a student name
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "student_name": "",
        "date": ""
      },
      "valid_heading": false,
      "has_students_copy": false,
      "has_fee_text": false,
      "valid_date": false,
      "has_student_name": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        print(result_text)
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_students_copy", False) and
            result.get("has_fee_text", False) and
            result.get("valid_date", False) and
            result.get("has_student_name", False)
        )
        
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "student_name": "",
                "date": ""
            },
            "valid_heading": False,
            "has_students_copy": False,
            "has_fee_text": False,
            "valid_date": False,
            "has_student_name": False,
            "valid": False,
            "error": str(e)
        }


#document 16 - Caste Certificate
def verify_caste_certificate_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of a Caste Certificate:
    1. Extract these details:
        - Applicant Name (appearing after the statement 'This is to certify that Sri/Srimathi/Kumari')
        - Community Serial No
        - Application No
    2. Verify these critical elements:
        - Presence of a heading containing 'CASTE CERTIFICATE' or 'CASTE AND DATE OF BIRTH CERTIFICATE' (case-insensitive)
        - Presence of a name following the statement 'This is to certify that Sri/Srimathi/Kumari'
        - Presence of a community serial no
        - Presence of an application no
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "name": "",
        "community_serial_no": "",
        "application_no": ""
      },
      "valid_heading": false,
      "has_name_after_statement": false,
      "has_community_serial_no": false,
      "has_application_no": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_name_after_statement", False) and
            result.get("has_community_serial_no", False) and
            result.get("has_application_no", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "name": "",
                "community_serial_no": "",
                "application_no": ""
            },
            "valid_heading": False,
            "has_name_after_statement": False,
            "has_community_serial_no": False,
            "has_application_no": False,
            "valid": False,
            "error": str(e)
        }

#document 15 - Attendance form
def verify_attendance_form_details(image_data):
    current_year = datetime.now().year
    prompt = """
    You are an intelligent OCR system. Given an image of an Attendance Sheet/Form:
    1. Extract these details:
        - Student Name
        - Date
        - Attendance Percentage
    2. Verify these critical elements:
        - Presence of the student name appearing exactly twice in the document
        - Presence of a date, which must be from the year {current_year}
        - Presence of an attendance percentage greater than 70%
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "student_name": "",
        "date": "",
        "attendance_percentage": ""
      },
      "has_student_name_twice": false,
      "valid_date": false,
      "valid_attendance_percentage": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        
        # Final validation
        result["valid"] = (
            result.get("has_student_name_twice", False) and
            result.get("valid_date", False) and
            result.get("valid_attendance_percentage", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "student_name": "",
                "date": "",
                "attendance_percentage": ""
            },
            "has_student_name_twice": False,
            "valid_date": False,
            "valid_attendance_percentage": False,
            "valid": False,
            "error": str(e)
        }



def verify_application_form(image_data, year, lateral_entry):
    """
    Verifies the Scholarship Application Form based on the year and required fields.
    """
    current_year = datetime.now().year

  
    # Determine expected heading based on year and lateral_entry
    if lateral_entry == 1 or str(lateral_entry) == "1":
        if year == 2 or str(year) == "2":
            renewal_type = "Fresh"
        else:
            renewal_type = "Renewal"
    else:
        if year == 1 or str(year) == "1":
            renewal_type = "Fresh"
        else:
            renewal_type = "Renewal"

    prompt = f"""
    You are an intelligent OCR system. Given an image of a Scholarship Application Form, extract and validate the following:
    1. Must contain a heading having these elements:
        - Post-Matric Scholarship, {renewal_type}, {current_year-1}-{current_year}
    2. Must contain:
        - Application Number
        - Date with the current year ({current_year-1})
        - Student Name
        - College details with "MUFFAKHAM JAH COLLEGE OF ENGINEERING AND TECHNOLOGY"
        - Family annual income
        - Course details: Course Name, Course Year, Duration of Course

    Return JSON in this format:
    {{
      "extracted": {{
        "heading": "",
        "application_number": "",
        "date": "",
        "student_name": "",
        "college_name": "",
        "family_annual_income": "",
        "course_name": "",
        "course_year": "",
        "course_duration": ""
      }},
      "valid_heading": false,
      "has_application_number": false,
      "valid_date": false,
      "has_student_name": false,
      "valid_college_name": false,
      "has_family_annual_income": false,
      "has_course_details": false,
      "valid": false
    }}
    """

    try:
        image = Image.open(io.BytesIO(image_data))
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text


        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)

        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_application_number", False) and
            result.get("valid_date", False) and
            result.get("has_student_name", False) and
            result.get("valid_college_name", False) and
            result.get("has_family_annual_income", False) and
            result.get("has_course_details", False)
        )

        return result

    except Exception as e:
        return {
            "extracted": {
                "heading": "",
                "application_number": "",
                "date": "",
                "student_name": "",
                "college_name": "",
                "family_annual_income": "",
                "course_name": "",
                "course_year": "",
                "course_duration": ""
            },
            "valid_heading": False,
            "has_application_number": False,
            "valid_date": False,
            "has_student_name": False,
            "valid_college_name": False,
            "has_family_annual_income": False,
            "has_course_details": False,
            "valid": False,
            "error": str(e)
        }
    
#document 14 - Intermediate Transfer certificate
def verify_inter_tc_details(image_data):
    prompt = """
    You are an intelligent OCR system. Given an image of an Intermediate Transfer Certificate (Inter TC):
    1. Extract these details:
        - Student Name
        - College Name
        - Father's Name
        - Admission Number
    2. Verify these critical elements:
        - Presence of a heading containing 'TRANSFER CERTIFICATE' (case-insensitive)
        - Presence of a student name
        - Presence of a college name
        - Presence of a father's name
        - Presence of an admission number
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "student_name": "",
        "college_name": "",
        "father_name": "",
        "admission_number": ""
      },
      "valid_heading": false,
      "has_student_name": false,
      "has_college_name": false,
      "has_father_name": false,
      "has_admission_number": false,
      "valid": false
    }
    """

    try:
        try:
            image = Image.open(io.BytesIO(image_data))
            print("Opened as image", flush=True)
        except Exception as img_e:
            print("Not an image, trying PDF...", flush=True)
            # Try to convert PDF to image (first page)
            try:
                images = convert_from_bytes(image_data, first_page=1, last_page=1)
                image = images[0]
                print("PDF converted to image", flush=True)
            except Exception as pdf_e:
                print("Failed to convert PDF to image", flush=True)
                raise pdf_e
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        print(result)
        
        # Final validation
        result["valid"] = (
            result.get("valid_heading", False) and
            result.get("has_student_name", False) and
            result.get("has_college_name", False) and
            result.get("has_father_name", False) and
            result.get("has_admission_number", False)
        )
        
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "student_name": "",
                "college_name": "",
                "father_name": "",
                "admission_number": ""
            },
            "valid_heading": False,
            "has_student_name": False,
            "has_college_name": False,
            "has_father_name": False,
            "has_admission_number": False,
            "valid": False,
            "error": str(e)
        }
    
#document 17 - Meeseva Slip
def verify_meeseva_slip_details(image_data):
    current_year = datetime.now().year
    print("hello inside meeseva slip")
    prompt = """
    You are an intelligent OCR system. Given an image of a Meeseva Slip:
    1. Extract these details:
        - Applicant Name
        - Application Number
        - Date of Payment
    2. Verify these critical elements:
        - Presence of a date of payment, which must be from the year {current_year}
        - Presence of an application number
        - Presence of an applicant name
        - Presence of the text 'Success Time Stamp:' with the value 'SUCCESS' (case-insensitive)
    
    Return JSON with extracted details and validation flags:
    {
      "extracted": {
        "applicant_name": "",
        "application_number": "",
        "date_of_payment": ""
      },
      "valid_date": false,
      "has_application_number": false,
      "has_applicant_name": false,
      "has_success_timestamp": false,
      "valid": false
    }
    """

    try:
        image = Image.open(io.BytesIO(image_data))
        response = model.generate_content([prompt, image], stream=False)
        result_text = response.text
        
        # Extract JSON from response
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_part = result_text[json_start:json_end]
        result = json.loads(json_part)
        print(result)
        
        # Final validation
        result["valid"] = (
            result.get("valid_date", False) and
            result.get("has_application_number", False) and
            result.get("has_applicant_name", False) and
            result.get("has_success_timestamp", False)
        )
        
        print(result)
        return result
        
    except Exception as e:
        return {
            "extracted": {
                "applicant_name": "",
                "application_number": "",
                "date_of_payment": ""
            },
            "valid_date": False,
            "has_application_number": False,
            "has_applicant_name": False,
            "has_success_timestamp": False,
            "valid": False,
            "error": str(e)
        }