from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import json
import google.generativeai as genai

# Flask server on a different port (5050)
app = Flask(__name__)
CORS(app)

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

@app.route('/upload_aadhaar', methods=['POST'])
def upload_aadhaar():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded", "aadhaar_valid": False}), 400

    file = request.files['file']
    image_data = file.read()
    details = extract_aadhar_details(image_data)
    return jsonify(details)

if __name__ == '__main__':
    app.run(port=5050, debug=True)
