import logging
from typing import Dict
import google.generativeai as genai
from PIL import Image
import json
import io
import re

class GeminiConfig:
    """Configuration for Gemini API"""
    API_KEY = "AIzaSyCA6kXkJEEfsYEqAxf8GXU2ZAK_f6LaJrI"

    @staticmethod
    def configure():
        if not GeminiConfig.API_KEY:
            raise ValueError("Gemini API key not found")
        genai.configure(api_key=GeminiConfig.API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR text extraction using Gemini Vision API."""
    
    def __init__(self):
        GeminiConfig.configure()
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_text_and_info_with_gemini(self, file_path: str) -> Dict:
        """
        Extract text and structured info from a document using Gemini Vision API.
        Returns a dict with text content and structured info.
        """
        try:
            # Open and prepare the image
            image = Image.open(file_path)
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            # Construct the prompt for detailed extraction
            prompt = """
            You are an intelligent OCR system. Given a document image, extract:
            1. All text content
            2. Key information in structured format:
               - Names (all names found)
               - ID numbers (Aadhaar, enrollment, etc.)
               - Dates (any dates found)
               - Gender (if present)
               - Document type

            Return in this JSON format:
            {
              "text_content": "full extracted text",
              "key_fields": {
                "names": ["name1", "name2"],
                "id_numbers": ["id1", "id2"],
                "dates": ["date1", "date2"],
                "gender": "M/F/O"
              },
              "document_type": "document type"
            }
            """

            # Generate content with Gemini
            response = self.model.generate_content(
                [prompt, img_bytes],
                stream=False
            )

            logger.info(f"[Gemini] Raw response.text: {response.text}")

            # Parse the response
            parsed_info = self._parse_gemini_response(response.text)
            logger.info(f"[Gemini] Parsed info: {parsed_info}")

            return parsed_info

        except Exception as e:
            logger.error(f"Error in Gemini extraction: {str(e)}")
            return {
                'text_content': '',
                'key_fields': {
                    'names': [],
                    'id_numbers': [],
                    'dates': []
                }
            }

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini's response, handling both JSON and text formats."""
        try:
            # Try to find and parse JSON content
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > 0:
                json_text = response_text[start:end]
                parsed = json.loads(json_text)
                
                # Ensure key_fields contains all expected fields
                key_fields = parsed.get('key_fields', {})
                for field in ['names', 'id_numbers', 'dates']:
                    if field not in key_fields or not isinstance(key_fields[field], list):
                        key_fields[field] = []
                
                return {
                    'text_content': parsed.get('text_content', ''),
                    'key_fields': key_fields,
                    'document_type': parsed.get('document_type', '')
                }
            
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
        
        # Fallback: Return empty structure
        return {
            'text_content': response_text,
            'key_fields': {
                'names': [],
                'id_numbers': [],
                'dates': []
            }
        }
    

    def verify_aadhaar(self, extracted_info: Dict) -> Dict:
        """Verify if the document is a valid Aadhaar card"""
        try:
            # Log extracted info for debugging
            #logger.info("Verifying Aadhaar info: %s", json.dumps(extracted_info, indent=2))
            
            key_fields = extracted_info.get('key_fields', {})
            text_content = extracted_info.get('text_content', '').lower()

            # Check if it's an Aadhaar document
            # aadhaar_keywords = ['aadhaar', 'unique identification', 'uid', 'आधार', '']
            # is_aadhaar = any(keyword in text_content for keyword in aadhaar_keywords)
            
            # if not is_aadhaar:
            #     logger.warning("Document does not appear to be an Aadhaar card")
            #     return {
            #         'verified': False,
            #         'error': 'Document does not appear to be an Aadhaar card'
            #     }

            # Extract and clean Aadhaar number
            id_numbers = key_fields.get('id_numbers', [])
            valid_aadhaar = None
            for num in id_numbers:
                cleaned_num = re.sub(r'\D', '', str(num))
                if re.match(r'^\d{12}$', cleaned_num):
                    valid_aadhaar = cleaned_num
                    break

            if not valid_aadhaar:
                logger.warning("No valid 12-digit Aadhaar number found")
                return {
                    'verified': False,
                    'error': 'No valid 12-digit Aadhaar number found'
                }

            # Log successful verification
            logger.info("Aadhaar verification successful")
            return {
                'verified': True,
                'message': 'Aadhaar card verified successfully',
                'data': {
                    'aadhaar_number': valid_aadhaar,
                    'names': key_fields.get('names', []),
                    'dates': key_fields.get('dates', []),
                    'gender': key_fields.get('gender', '')
                }
            }

        except Exception as e:
            logger.error(f"Error in Aadhaar verification: {str(e)}", exc_info=True)
            return {
                'verified': False,
                'error': f'Verification error: {str(e)}'
            }

    def extract_and_verify_document(self, file_path: str, document_type: str) -> Dict:
        """Extract text and verify document based on type"""
        try:
            # Extract text and info using Gemini
            extracted_info = self.extract_text_and_info_with_gemini(file_path)
            
            if document_type == 'aadhaar':
                return self.verify_aadhaar(extracted_info)
            
            # Add other document type verifications here
            
            return {
                'verified': False,
                'error': 'Unsupported document type'
            }

        except Exception as e:
            logger.error(f"Error in document extraction and verification: {str(e)}")
            return {
                'verified': False,
                'error': f'Processing error: {str(e)}'
            }
