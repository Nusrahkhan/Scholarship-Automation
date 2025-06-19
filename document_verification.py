from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import json
import google.generativeai as genai


# Configure Gemini API
GEMINI_API_KEY = "AIzaSyCA6kXkJEEfsYEqAxf8GXU2ZAK_f6LaJrI"
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
        image = Image.open(io.BytesIO(image_data))
        response = model.generate_content([prompt, image], stream=False)

        result_text = response.text
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

# Add this function to document_verification.py
from datetime import datetime

# Add to document_verification.py
def extract_ack_form_details(image_data):
    current_year = datetime.now().year
    expected_academic_year = f"{current_year}-{current_year+1}"
    
    prompt = f"""
    You are an intelligent OCR system. Given an image of a Scholarship Acknowledgement Form:
    1. Extract these details:
        - Application Number
        - Applicant Name
        - Academic Year
        - Institute Name
        - Bank Name
        - Date of Birth
    2. Verify these critical elements:
        - Institute name must be 'Muffakkham Jah College of Engineering and Technology'
        - Presence of the word 'Acknowledgement' (case-insensitive)
        - Academic year must be {expected_academic_year}
        - Presence of official stamp (look for circular/rectangular seals)
        - Presence of authorized signature
    
    Return JSON with validation flags:
    {{
      "valid_institute": false,
      "has_acknowledgement": false,
      "valid_academic_year": false,
      "has_stamp": false,
      "has_signature": false,
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
            result.get("valid_academic_year", False) and
            result.get("has_stamp", False) and
            result.get("has_signature", False)
        )
        
        return result
        
    except Exception as e:
        return {
        "valid_institute": False,
        "has_acknowledgement": False,
        "valid_academic_year": False,
        "has_stamp": False,
        "has_signature": False,
        "valid": False,
        "error": str(e),
        }
    

#document 2 - Income Certificate
def verify_income_certificate_details(image_data):

#document 3 - Declaration Form
def verify_declaration_form_details(image_data):

#document 4 - Current Bonafide
def verify_current_bonafide_details(image_data):

#document 5 - Previous Bonafides(6th-10th)
def verify_previous_bonafides_details(image_data):

#document 6 - Tenth Memo
def verify_tenth_memo_details(image_data):

#document 7 - Inter Memo
def verify_inter_memo_details(image_data):

#document 8 - Previous Semester Memo
def verify_previous_sem_memo_details(image_data):

#document 9 - Ration Card
def verify_ration_card_details(image_data):

#document 11 - Bank Passbook
def verify_bank_passbook_details(image_data):

#document 12 - Allotment Order
def verify_allotment_order_details(image_data):

#document 12 - OU Common Service Fee
def verify_ou_common_service_fee_details(image_data):