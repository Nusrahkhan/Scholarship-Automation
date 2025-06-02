import os
import re
import pytesseract
import logging
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from ..utils.image_utils import preprocess_image
from ..utils.pdf_utils import convert_pdf_to_images
# Add these imports at the top
import google.generativeai as genai
from PIL import Image
import os
from typing import Optional, List, Dict

class GeminiConfig:
    """Configuration for Gemini API"""
    API_KEY = os.getenv('GEMINI_API_KEY')  # Get API key from environment variable
    MODEL_NAME = "gemini-1.5-flash"  # Model for image/document understanding
    
    @staticmethod
    def configure():
        """Configure Gemini with API key"""
        if not GeminiConfig.API_KEY:
            raise ValueError("Gemini API key not found in environment variables")
        genai.configure(api_key=GeminiConfig.API_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRService:
    """Service for OCR text extraction from documents."""

    def __init__(self, tesseract_path=None):
        """Initialize OCR service with optional Tesseract path."""
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_text_with_gemini(self, file_path: str) -> Optional[Dict]:
        """
        Extract text from document using Gemini Vision API.
        Returns both extracted text and structured information.
        """
        try:
            # Configure Gemini
            GeminiConfig.configure()
            model = genai.GenerativeModel(GeminiConfig.MODEL_NAME)

            # Load and prepare image
            image = Image.open(file_path)
            
            # Prompt for document analysis
            prompt = """
            Please analyze this document carefully and extract the following:
            1. All text content maintaining formatting
            2. Any key fields like dates, names, ID numbers
            3. Document type (application form, certificate, etc.)
            4. Whether it's a fresh application or renewal
            5. Important numerical values (percentages, marks, etc.)
            
            Format the response as structured data.
            """

            # Generate response from Gemini
            response = model.generate_content([prompt, image])
            
            if response and response.text:
                # Parse structured response
                result = {
                    'extracted_text': response.text,
                    'document_info': self._parse_gemini_response(response.text)
                }
                logger.info(f"Gemini successfully extracted text from {file_path}")
                return result
            else:
                logger.warning(f"Gemini returned empty response for {file_path}")
                return None

        except Exception as e:
            logger.error(f"Error in Gemini text extraction: {str(e)}")
            return None

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse structured information from Gemini's response"""
        try:
            info = {
                'document_type': None,
                'application_type': None,
                'key_fields': {},
                'numerical_values': {}
            }

            # Extract document type
            doc_type_match = re.search(r'Document type:?\s*([^\n]+)', response_text)
            if doc_type_match:
                info['document_type'] = doc_type_match.group(1).strip()

            # Extract application type (fresh/renewal)
            if re.search(r'\bfresh\b', response_text, re.IGNORECASE):
                info['application_type'] = 'Fresh'
            elif re.search(r'\brenewal\b', response_text, re.IGNORECASE):
                info['application_type'] = 'Renewal'

            # Extract key fields (dates, names, IDs)
            date_matches = re.finditer(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', response_text)
            for match in date_matches:
                info['key_fields']['date'] = match.group(1)

            # Extract numerical values
            percentage_matches = re.finditer(r'(\d+\.?\d*)%', response_text)
            for i, match in enumerate(percentage_matches):
                info['numerical_values'][f'percentage_{i+1}'] = float(match.group(1))

            return info

        except Exception as e:
            logger.error(f"Error parsing Gemini response: {str(e)}")
            return {}

    def extract_text_hybrid(self, file_path: str, use_gemini: bool = True) -> Dict:
        """
        Extract text using both Tesseract OCR and Gemini for better accuracy.
        Combines and compares results from both methods.
        """
        results = {
            'text': None,
            'structured_info': None,
            'confidence': 0.0,
            'method_used': None
        }

        try:
            # Get Tesseract OCR results
            ocr_text = self.extract_text_from_file(file_path)
            ocr_confidence = self._calculate_text_confidence(ocr_text, None) if ocr_text else 0.0

            # Get Gemini results if enabled
            gemini_result = None
            if use_gemini:
                gemini_result = self.extract_text_with_gemini(file_path)

            # Compare and combine results
            if gemini_result and gemini_result['extracted_text']:
                gemini_text = gemini_result['extracted_text']
                gemini_confidence = self._calculate_text_confidence(gemini_text, None)

                # Choose better result or combine them
                if gemini_confidence > ocr_confidence * 1.2:  # Gemini significantly better
                    results['text'] = gemini_text
                    results['structured_info'] = gemini_result['document_info']
                    results['confidence'] = gemini_confidence
                    results['method_used'] = 'gemini'
                else:
                    # Combine results
                    combined_text = self._combine_ocr_results([ocr_text, gemini_text])
                    results['text'] = combined_text
                    results['structured_info'] = gemini_result['document_info']
                    results['confidence'] = max(ocr_confidence, gemini_confidence)
                    results['method_used'] = 'hybrid'
            else:
                # Fallback to OCR only
                results['text'] = ocr_text
                results['confidence'] = ocr_confidence
                results['method_used'] = 'ocr'

            return results

        except Exception as e:
            logger.error(f"Error in hybrid text extraction: {str(e)}")
            return results

    def extract_text_from_file(self, file_path, quality_mode='auto', detect_fresh_renewal=False):
        """Extract text from a file (PDF or image) with enhanced preprocessing."""
        try:
            file_extension = file_path.split('.')[-1].lower()

            # Handle PDF files
            if file_extension == 'pdf':
                logger.info(f"Processing PDF file: {file_path} with quality mode: {quality_mode}")
                return self._extract_text_from_pdf(file_path, quality_mode)

            # Handle image files
            elif file_extension in ['png', 'jpg', 'jpeg', 'tif', 'tiff']:
                logger.info(f"Processing image file: {file_path} with quality mode: {quality_mode}")
                return self._extract_text_from_image(file_path, quality_mode)

            else:
                logger.error(f"Unsupported file format: {file_extension}")
                return None

        except Exception as e:
            logger.error(f"Error extracting text from file: {str(e)}")
            return None

    def _extract_text_from_pdf(self, pdf_path, quality_mode='auto'):
        """Extract text from a PDF file by converting to images and applying OCR."""
        try:
            from app.utils.pdf_utils import convert_pdf_to_images_with_fallback, enhance_pdf_image_quality

            # Convert PDF to images with enhanced quality settings
            image_paths = convert_pdf_to_images_with_fallback(pdf_path)

            if not image_paths:
                logger.error("Failed to convert PDF to images")
                return None

            # Extract text from each image and combine
            all_text = []
            for img_path in image_paths:
                # Apply PDF-specific image enhancement
                try:
                    enhanced_image = enhance_pdf_image_quality(img_path)
                    # Save enhanced image temporarily
                    enhanced_path = img_path.replace('.png', '_enhanced.png')
                    enhanced_image.save(enhanced_path)

                    # Extract text from enhanced image
                    text = self._extract_text_from_image(enhanced_path, quality_mode)
                    if text:
                        all_text.append(text)

                    # Clean up enhanced image
                    try:
                        os.remove(enhanced_path)
                    except:
                        pass

                except Exception as e:
                    logger.warning(f"PDF enhancement failed, using original: {str(e)}")
                    # Fallback to original image
                    text = self._extract_text_from_image(img_path, quality_mode)
                    if text:
                        all_text.append(text)

                # Clean up temporary image file
                try:
                    os.remove(img_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary image: {str(e)}")

            return "\n\n".join(all_text)

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def _extract_text_from_image(self, image_path, quality_mode='auto'):
        """Fast OCR with smart strategy selection for optimal speed and accuracy."""
        try:
            # FAST APPROACH: Start with standard OCR, escalate only if needed
            logger.info(f"Starting fast OCR extraction for {image_path}")

            # Step 1: Quick standard OCR
            logger.info("Step 1: Quick standard OCR")
            preprocessed_image = preprocess_image(image_path, 'basic')
            standard_config = '--oem 3 --psm 6'
            standard_text = pytesseract.image_to_string(preprocessed_image, config=standard_config)
            standard_text = self._post_process_text(standard_text)

            # Quick quality check
            standard_keywords = self._count_important_keywords(standard_text)
            standard_length = len(standard_text.strip())

            logger.info(f"Standard OCR: {standard_length} chars, {standard_keywords} keywords")

            # If standard OCR is good enough, return it (FAST PATH)
            if standard_length > 100 and standard_keywords >= 3:
                logger.info("Standard OCR sufficient - using fast path")
                return standard_text

            # Quick check: if standard OCR is very good, skip other steps
            if standard_length > 500 and standard_keywords >= 5:
                logger.info("Standard OCR excellent - skipping other steps")
                return standard_text

            # Step 2: Enhanced OCR for better quality
            logger.info("Step 2: Enhanced OCR (standard insufficient)")
            enhanced_image = preprocess_image(image_path, 'enhanced')
            enhanced_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()/-: '
            enhanced_text = pytesseract.image_to_string(enhanced_image, config=enhanced_config)
            enhanced_text = self._post_process_text(enhanced_text)

            enhanced_keywords = self._count_important_keywords(enhanced_text)
            enhanced_length = len(enhanced_text.strip())

            logger.info(f"Enhanced OCR: {enhanced_length} chars, {enhanced_keywords} keywords")

            # Choose better result between standard and enhanced
            if enhanced_keywords > standard_keywords or enhanced_length > standard_length * 1.2:
                best_text = enhanced_text
                best_keywords = enhanced_keywords
            else:
                best_text = standard_text
                best_keywords = standard_keywords

            # If enhanced is good enough, return it (MEDIUM PATH)
            if len(best_text.strip()) > 200 and best_keywords >= 4:
                logger.info("Enhanced OCR sufficient - using medium path")
                return best_text

            # Step 3: Small font optimization (only if really needed)
            logger.info("Step 3: Small font optimization (enhanced insufficient)")
            small_font_text = self._extract_small_font_text_fast(image_path)
            small_font_keywords = self._count_important_keywords(small_font_text)

            logger.info(f"Small font OCR: {len(small_font_text)} chars, {small_font_keywords} keywords")

            # Use small font result if significantly better
            if small_font_keywords > best_keywords or len(small_font_text.strip()) > len(best_text.strip()) * 1.3:
                logger.info("Small font OCR yielded better results")
                best_text = small_font_text

            logger.info(f"Final OCR result: {len(best_text)} characters")
            return best_text

        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            return None

    def _get_ocr_config(self, quality_mode):
        """Get Tesseract configuration based on quality mode with handwritten text support."""

        if quality_mode == 'aggressive':
            # Aggressive settings for low quality and handwritten text
            return '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/() '
        elif quality_mode == 'enhanced':
            # Enhanced settings for mixed printed/handwritten text
            return '--oem 3 --psm 6'  # Uniform block of text
        else:
            # Standard settings for printed text
            return '--oem 3 --psm 6'

    def _get_ocr_config_enhanced(self, strategy_name):
        """Get enhanced OCR configuration based on strategy."""
        configs = {
            'standard': '--oem 3 --psm 6',  # Uniform block of text
            'enhanced': '--oem 3 --psm 4',  # Single column of text
            'aggressive': '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/()[]{}@#$%&*+=|\\<>?~`\' ',
            'handwritten': '--oem 3 --psm 7'  # Single text line
        }
        return configs.get(strategy_name, '--oem 3 --psm 6')

    def _extract_handwritten_text_enhanced(self, preprocessed_image):

        """Enhanced extraction for handwritten text with multiple attempts."""
        try:
            best_text = ""
            best_confidence = 0
            
            for config in handwritten_configs:
                try:
                    text = pytesseract.image_to_string(preprocessed_image, config=config)
                    confidence = self._calculate_text_confidence(text, preprocessed_image)
                    
                    if confidence > best_confidence:
                        best_text = text
                        best_confidence = confidence
                        
                except Exception as e:
                    logger.debug(f"Config {config} failed: {str(e)}")
                    continue
                    
            return best_text

        except Exception as e:
            logger.error(f"Handwritten text enhancement failed: {str(e)}")
            return ""

    def _calculate_text_confidence(self, text, image):
        """Calculate confidence score for extracted text."""
        try:
            if not text or len(text.strip()) < 5:
                return 0.0

            # Basic confidence metrics
            confidence_score = 0.0

            # Length factor (longer text generally more reliable)
            length_factor = min(len(text.strip()) / 100.0, 1.0)
            confidence_score += length_factor * 0.3

            # Character diversity (more diverse characters = better OCR)
            unique_chars = len(set(text.lower()))
            diversity_factor = min(unique_chars / 20.0, 1.0)
            confidence_score += diversity_factor * 0.2

            # Word count factor
            words = text.split()
            word_factor = min(len(words) / 20.0, 1.0)
            confidence_score += word_factor * 0.2

            # Check for common document keywords
            keywords = ['government', 'telangana', 'scholarship', 'application', 'certificate',
                       'bonafide', 'aadhaar', 'name', 'date', 'roll', 'number', 'college']
            keyword_matches = sum(1 for keyword in keywords if keyword.lower() in text.lower())
            keyword_factor = min(keyword_matches / 5.0, 1.0)
            confidence_score += keyword_factor * 0.3

            return min(confidence_score, 1.0)

        except Exception as e:
            logger.warning(f"Error calculating text confidence: {str(e)}")
            return 0.5  # Default moderate confidence

    def _ultra_aggressive_ocr(self, image_path):
        """Ultra-aggressive OCR approach for very poor quality documents."""
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps

            # Load and apply extreme preprocessing
            image = Image.open(image_path)

            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')

            # Extreme upscaling
            width, height = image.size
            if width < 2000 or height < 2000:
                scale_factor = max(2000 / width, 2000 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)

            # Extreme contrast enhancement
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(3.0)

            # Extreme sharpening
            image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=300, threshold=1))

            # Auto-contrast with aggressive settings
            image = ImageOps.autocontrast(image, cutoff=5)

            # Try multiple extreme OCR configurations
            extreme_configs = [
                '--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/()[]{}@#$%&*+=|\\<>?~`\' ',
                '--oem 1 --psm 6',  # Legacy engine
                '--oem 2 --psm 6',  # Cube engine
                '--oem 3 --psm 4',  # Single column
                '--oem 3 --psm 8',  # Single word
            ]

            best_text = ""
            best_length = 0

            for config in extreme_configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    if text and len(text.strip()) > best_length:
                        best_text = text
                        best_length = len(text.strip())
                except:
                    continue

            return self._post_process_text(best_text)

        except Exception as e:
            logger.error(f"Ultra-aggressive OCR failed: {str(e)}")
            return ""

    def _extract_small_font_text(self, image_path):
        """Specialized OCR for small font text extraction."""
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps

            # Load image
            image = Image.open(image_path)

            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')

            # Extreme upscaling for small fonts (4x scale)
            width, height = image.size
            scale_factor = 4.0  # Aggressive scaling for small fonts
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)

            # Enhanced contrast for small text
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            # Sharpening specifically for small fonts
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=200, threshold=2))

            # Auto-contrast
            image = ImageOps.autocontrast(image, cutoff=2)

            # Multiple OCR attempts with small font optimized settings
            small_font_configs = [
                '--oem 3 --psm 6',  # Uniform block of text
                '--oem 3 --psm 4',  # Single column of text
                '--oem 3 --psm 3',  # Fully automatic page segmentation
                '--oem 3 --psm 1',  # Automatic page segmentation with OSD
                '--oem 1 --psm 6',  # Legacy engine
            ]

            best_text = ""
            best_length = 0

            for config in small_font_configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    if text and len(text.strip()) > best_length:
                        best_text = text
                        best_length = len(text.strip())
                except:
                    continue

            return best_text

        except Exception as e:
            logger.error(f"Small font OCR failed: {str(e)}")
            return ""

    def _extract_small_font_text_fast(self, image_path):
        """Fast small font OCR with minimal processing."""
        try:
            from PIL import Image, ImageEnhance, ImageOps

            # Load and convert image
            image = Image.open(image_path)
            if image.mode != 'L':
                image = image.convert('L')

            # Moderate upscaling (2x instead of 4x for speed)
            width, height = image.size
            scale_factor = 2.0  # Reduced from 4.0 for speed
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)

            # Quick contrast enhancement
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)  # Reduced from 2.0

            # Auto-contrast only
            image = ImageOps.autocontrast(image, cutoff=2)

            # Single OCR attempt with optimized config
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()/-: '
            text = pytesseract.image_to_string(image, config=config)

            return text

        except Exception as e:
            logger.error(f"Fast small font OCR failed: {str(e)}")
            return ""

    def _extract_ultra_high_dpi_text(self, image_path):
        """Ultra high DPI processing for very small text."""
        try:
            from PIL import Image, ImageEnhance, ImageFilter, ImageOps

            # Load image
            image = Image.open(image_path)

            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')

            # Ultra high DPI simulation (6x scale)
            width, height = image.size
            scale_factor = 6.0  # Very aggressive scaling
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.LANCZOS)

            # Multiple enhancement passes
            for _ in range(2):
                # Contrast enhancement
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.8)

                # Sharpening
                image = image.filter(ImageFilter.SHARPEN)

            # Final auto-contrast
            image = ImageOps.autocontrast(image, cutoff=1)

            # Ultra high DPI OCR configurations
            ultra_configs = [
                '--oem 3 --psm 6 --dpi 600',  # High DPI
                '--oem 3 --psm 4 --dpi 600',  # High DPI single column
                '--oem 3 --psm 3 --dpi 600',  # High DPI automatic
                '--oem 1 --psm 6 --dpi 600',  # Legacy with high DPI
            ]

            best_text = ""
            best_length = 0

            for config in ultra_configs:
                try:
                    text = pytesseract.image_to_string(image, config=config)
                    if text and len(text.strip()) > best_length:
                        best_text = text
                        best_length = len(text.strip())
                except:
                    continue

            return best_text

        except Exception as e:
            logger.error(f"Ultra high DPI OCR failed: {str(e)}")
            return ""

    def _combine_ocr_results(self, all_texts):
        """Combine multiple OCR results to get the best keywords."""
        try:
            if not all_texts:
                return ""

            # Remove empty texts
            valid_texts = [text for text in all_texts if text and len(text.strip()) > 10]

            if not valid_texts:
                return ""

            # If only one valid text, return it
            if len(valid_texts) == 1:
                return valid_texts[0]

            # Find the longest text as base
            base_text = max(valid_texts, key=len)

            # Important keywords to look for across all texts
            important_keywords = [
                'Government', 'Telangana', 'Department', 'Minority', 'Student', 'Application',
                'Verification', 'Report', 'Post-Matric', 'Scholarship', 'Fresh', 'Renewal',
                '2025', 'Acknowledgement', 'Attendance'
            ]

            # Check which keywords are missing from base text
            missing_keywords = []
            for keyword in important_keywords:
                if keyword.lower() not in base_text.lower():
                    # Look for this keyword in other texts
                    for text in valid_texts:
                        if keyword.lower() in text.lower():
                            missing_keywords.append(keyword)
                            break

            # If we found missing keywords, append them to base text
            if missing_keywords:
                base_text += " " + " ".join(missing_keywords)

            return base_text

        except Exception as e:
            logger.warning(f"Error combining OCR results: {str(e)}")
            return max(all_texts, key=len) if all_texts else ""

    def _count_important_keywords(self, text):
        """Count important keywords in text for quality assessment."""
        if not text:
            return 0

        important_keywords = [
            'Government', 'Telangana', 'Department', 'Minority', 'Student', 'Application',
            'Verification', 'Report', 'Post-Matric', 'Scholarship', 'Fresh', 'Renewal',
            'Acknowledgement', 'Attendance',
            # LE-specific keywords (expanded)
            'State', 'Board', 'Technical', 'Education', 'Training', 'Polytechnic',
            'Consolidated', 'Memorandum', 'Grades', 'Transfer', 'Certificate', 'Bonafide',
            'Certify', 'Diploma', 'Institution', 'College', 'Course', 'Branch',
            # Additional LE keywords
            'SBTET', 'Candidate', 'Marks', 'Result', 'Record', 'Engineering',
            'Institute', 'Leaving', 'Migration', 'TC', 'Cert', 'Name'
        ]

        count = 0
        for keyword in important_keywords:
            if re.search(keyword, text, re.IGNORECASE):
                count += 1

        return count

    def detect_and_correct_rotation(self, image_path):
        """
        Detect and correct image rotation for better OCR results.
        Tests multiple rotation angles and selects the best one based on OCR confidence.
        """
        try:
            logger.info(f"Detecting and correcting rotation for: {image_path}")

            # Load image
            if isinstance(image_path, str):
                if image_path.lower().endswith('.pdf'):
                    from app.utils.pdf_utils import convert_pdf_to_images
                    images = convert_pdf_to_images(image_path)
                    if not images:
                        return None
                    original_image = images[0]
                else:
                    original_image = Image.open(image_path)
            else:
                original_image = image_path

            if original_image is None:
                return None

            # Test different rotation angles
            rotation_angles = [0, 90, 180, 270]
            best_result = None
            best_confidence = 0
            best_keywords = 0

            for angle in rotation_angles:
                try:
                    # Rotate image
                    if angle == 0:
                        rotated_image = original_image
                    else:
                        rotated_image = original_image.rotate(-angle, expand=True)

                    # Quick OCR test to measure quality
                    test_text = pytesseract.image_to_string(rotated_image, config='--psm 6')

                    # Calculate quality metrics
                    text_length = len(test_text.strip())
                    keywords_found = self._count_important_keywords(test_text)

                    # Calculate confidence score based on:
                    # 1. Text length (more text usually better)
                    # 2. Keywords found (domain-specific quality)
                    # 3. Readable character ratio
                    readable_chars = sum(1 for c in test_text if c.isalnum() or c.isspace())
                    total_chars = len(test_text) if len(test_text) > 0 else 1
                    readable_ratio = readable_chars / total_chars

                    confidence_score = (
                        text_length * 0.3 +           # Text length weight
                        keywords_found * 100 +        # Keywords weight (high importance)
                        readable_ratio * 200          # Readability weight
                    )

                    logger.info(f"Angle {angle}°: {text_length} chars, {keywords_found} keywords, {readable_ratio:.2f} readable, score: {confidence_score:.1f}")

                    if confidence_score > best_confidence:
                        best_confidence = confidence_score
                        best_keywords = keywords_found
                        best_result = {
                            'angle': angle,
                            'image': rotated_image,
                            'text': test_text,
                            'confidence': confidence_score,
                            'keywords': keywords_found,
                            'text_length': text_length
                        }

                except Exception as e:
                    logger.warning(f"Error testing rotation angle {angle}°: {str(e)}")
                    continue

            if best_result:
                logger.info(f"Best rotation: {best_result['angle']}° (score: {best_result['confidence']:.1f}, keywords: {best_result['keywords']})")
                return best_result
            else:
                logger.warning("No successful rotation found, using original")
                return {
                    'angle': 0,
                    'image': original_image,
                    'text': '',
                    'confidence': 0,
                    'keywords': 0,
                    'text_length': 0
                }

        except Exception as e:
            logger.error(f"Error in rotation detection: {str(e)}")
            return None

    def extract_text_with_rotation_correction(self, file_path, quality_mode='auto', use_gemini=True):
        """
        Extract text with automatic rotation correction and Gemini integration.
        """
        try:
            logger.info(f"Extracting text with rotation correction: {file_path}")

            # Step 1: Detect and correct rotation
            rotation_result = self.detect_and_correct_rotation(file_path)

            if not rotation_result:
                logger.warning("Rotation detection failed, falling back to hybrid extraction")
                return self.extract_text_hybrid(file_path, use_gemini=use_gemini)

            corrected_image = rotation_result['image']
            detected_angle = rotation_result['angle']

            logger.info(f"Using rotation-corrected image (rotated {detected_angle}°)")

            # Step 2: Try Gemini first if enabled
            if use_gemini:
                try:
                    # Save rotated image temporarily
                    temp_path = f"{file_path}_rotated.png"
                    corrected_image.save(temp_path)
                    
                    # Use Gemini for text extraction
                    gemini_result = self.extract_text_with_gemini(temp_path)
                    
                    # Clean up temporary file
                    try:
                        os.remove(temp_path)
                    except:
                        pass

                    if gemini_result and gemini_result['extracted_text']:
                        logger.info("Successfully extracted text using Gemini")
                        return {
                            'text': gemini_result['extracted_text'],
                            'structured_info': gemini_result['document_info'],
                            'confidence': 0.9,  # Gemini typically has high confidence
                            'method_used': 'gemini'
                        }
                        
                except Exception as e:
                    logger.warning(f"Gemini extraction failed, falling back to OCR: {str(e)}")

            # Step 3: Fallback to enhanced OCR if Gemini fails or is disabled
            if quality_mode == 'auto':
                # Try standard OCR first
                try:
                    text = pytesseract.image_to_string(corrected_image, config='--psm 6')
                    keywords = self._count_important_keywords(text)

                    if len(text) > 500 and keywords >= 3:
                        logger.info(f"Standard OCR sufficient: {len(text)} chars, {keywords} keywords")
                        return {
                            'text': self._post_process_text(text),
                            'confidence': 0.7,
                            'method_used': 'ocr_standard'
                        }
                except:
                    pass

                # Try enhanced preprocessing
                try:
                    enhanced_image = preprocess_image(corrected_image, quality_level='enhanced')
                    text = pytesseract.image_to_string(enhanced_image, config='--psm 6')
                    return {
                        'text': self._post_process_text(text),
                        'confidence': 0.6,
                        'method_used': 'ocr_enhanced'
                    }
                except:
                    pass

            # Fallback to original method if all else fails
            logger.warning("Advanced methods failed, using basic OCR")
            return self.extract_text_from_file(file_path, quality_mode)

        except Exception as e:
            logger.error(f"Error in rotation-corrected extraction: {str(e)}")
            return self.extract_text_from_file(file_path, quality_mode)

    def extract_date_from_upper_right(self, file_path):
        """
        Extract date specifically from upper right corner of the document.
        Useful for attendance forms where date is typically located there.
        """
        try:
            logger.info(f"Extracting date from upper right corner: {file_path}")

            # Load image
            if file_path.lower().endswith('.pdf'):
                from app.utils.pdf_utils import convert_pdf_to_images
                images = convert_pdf_to_images(file_path)
                if not images:
                    return None
                image = images[0]  # Use first page
            else:
                from PIL import Image
                image = Image.open(file_path)

            if image is None:
                return None

            # Get image dimensions
            width, height = image.size

            # Extract upper right corner (top 25% height, right 40% width)
            upper_right_box = (
                int(width * 0.6),  # Start from 60% width (right 40%)
                0,                 # Top of image
                width,             # Full width
                int(height * 0.25) # Top 25% height
            )

            upper_right_region = image.crop(upper_right_box)

            # Apply basic preprocessing for better date recognition
            # Convert PIL image to format compatible with pytesseract
            processed_region = upper_right_region

            # OCR with date-specific configuration
            date_config = '--psm 6 -c tessedit_char_whitelist=0123456789/-.'
            text = pytesseract.image_to_string(processed_region, config=date_config)

            # Look for date patterns
            import re
            date_patterns = [
                r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b',  # DD/MM/YYYY or DD-MM-YYYY
                r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b',  # DD/MM/YY or DD-MM-YY
                r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
                r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',      # DD.MM.YYYY
                r'\b(\d{1,2})\.(\d{1,2})\.(\d{2})\b',      # DD.MM.YY
            ]

            found_dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    if len(match) == 3:
                        # Convert to standard format and validate
                        try:
                            day, month, year = match
                            if len(year) == 2:
                                year = '20' + year  # Assume 20xx for 2-digit years

                            # Basic validation
                            day_int = int(day)
                            month_int = int(month)
                            year_int = int(year)

                            if 1 <= day_int <= 31 and 1 <= month_int <= 12 and 2020 <= year_int <= 2030:
                                date_str = f"{day}/{month}/{year}"
                                found_dates.append(date_str)

                        except ValueError:
                            continue

            if found_dates:
                logger.info(f"Found dates in upper right corner: {found_dates}")
                return found_dates[0]  # Return first valid date
            else:
                logger.info("No dates found in upper right corner")
                return None

        except Exception as e:
            logger.error(f"Error extracting date from upper right corner: {str(e)}")
            return None

    def detect_fresh_renewal_keywords(self, file_path):
        """
        Aggressive OCR specifically for detecting Fresh/Renewal keywords.
        Uses multiple OCR strategies and preprocessing techniques.
        """
        try:
            logger.info(f"Aggressive Fresh/Renewal detection for: {file_path}")

            # Load image
            if file_path.lower().endswith('.pdf'):
                # Convert PDF to image first
                from app.utils.pdf_utils import convert_pdf_to_images
                images = convert_pdf_to_images(file_path)
                if not images:
                    return []
                image = images[0]  # Use first page
            else:
                image = cv2.imread(file_path)

            if image is None:
                return []

            fresh_renewal_keywords = []

            # Strategy 1: Focus on top portion (headers)
            height, width = image.shape[:2]
            top_portion = image[0:int(height*0.3), :]  # Top 30%

            # Strategy 2: Multiple preprocessing approaches
            preprocessing_strategies = [
                {'name': 'high_contrast', 'params': {'contrast': 2.0, 'brightness': 50}},
                {'name': 'threshold', 'params': {'threshold_type': cv2.THRESH_BINARY}},
                {'name': 'morphology', 'params': {'kernel_size': (2, 2)}},
                {'name': 'blur_sharpen', 'params': {'blur_kernel': (1, 1), 'sharpen': True}},
            ]

            for strategy in preprocessing_strategies:
                try:
                    # Apply preprocessing
                    processed_image = self._apply_aggressive_preprocessing(top_portion, strategy)

                    # OCR with different configurations
                    ocr_configs = [
                        '--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789',
                        '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                        '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                        '--psm 13'  # Raw line
                    ]

                    for config in ocr_configs:
                        text = pytesseract.image_to_string(processed_image, config=config)

                        # Look for Fresh/Renewal patterns
                        fresh_patterns = [
                            r'\bfresh\b', r'\bfreash\b', r'\bfres\b', r'\bfrash\b',
                            r'\bfresh.*2025\b', r'2025.*fresh'
                        ]

                        renewal_patterns = [
                            r'\brenewal\b', r'\brenwal\b', r'\brenew\b',
                            r'\brenewal.*2025\b', r'2025.*renewal'
                        ]

                        for pattern in fresh_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            if matches:
                                fresh_renewal_keywords.extend([('Fresh', match) for match in matches])

                        for pattern in renewal_patterns:
                            matches = re.findall(pattern, text, re.IGNORECASE)
                            if matches:
                                fresh_renewal_keywords.extend([('Renewal', match) for match in matches])

                except Exception as e:
                    logger.warning(f"Strategy {strategy['name']} failed: {str(e)}")
                    continue

            # Remove duplicates
            unique_keywords = list(set(fresh_renewal_keywords))

            if unique_keywords:
                logger.info(f"Found Fresh/Renewal keywords: {unique_keywords}")
            else:
                logger.info("No Fresh/Renewal keywords detected")

            return unique_keywords

        except Exception as e:
            logger.error(f"Error in aggressive Fresh/Renewal detection: {str(e)}")
            return []

    def _apply_aggressive_preprocessing(self, image, strategy):
        """Apply aggressive preprocessing for keyword detection."""
        try:
            if strategy['name'] == 'high_contrast':
                # Increase contrast and brightness
                contrast = strategy['params']['contrast']
                brightness = strategy['params']['brightness']
                image = cv2.convertScaleAbs(image, alpha=contrast, beta=brightness)

            elif strategy['name'] == 'threshold':
                # Convert to grayscale and apply threshold
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                _, image = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            elif strategy['name'] == 'morphology':
                # Morphological operations
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                kernel = np.ones(strategy['params']['kernel_size'], np.uint8)
                image = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

            elif strategy['name'] == 'blur_sharpen':
                # Blur then sharpen
                kernel_size = strategy['params']['blur_kernel']
                image = cv2.GaussianBlur(image, kernel_size, 0)
                if strategy['params']['sharpen']:
                    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                    image = cv2.filter2D(image, -1, kernel)

            return image

        except Exception as e:
            logger.warning(f"Preprocessing strategy {strategy['name']} failed: {str(e)}")
            return image

    def _extract_handwritten_text(self, image_path):
        """Specialized extraction for handwritten text areas."""
        try:
            # Enhanced preprocessing specifically for handwritten text
            preprocessed_image = preprocess_image(image_path, 'aggressive')

            # Multiple OCR attempts with different PSM modes for handwritten text
            handwritten_configs = [
                '--oem 3 --psm 8',  # Single word
                '--oem 3 --psm 7',  # Single text line
                '--oem 3 --psm 13', # Raw line. Treat the image as a single text line
                '--oem 3 --psm 6',  # Uniform block of text
            ]

            best_text = ""
            best_length = 0

            for config in handwritten_configs:
                try:
                    text = pytesseract.image_to_string(preprocessed_image, config=config)
                    if text and len(text) > best_length:
                        best_text = text
                        best_length = len(text)
                except:
                    continue

            return best_text if best_text else ""

        except Exception as e:
            logger.error(f"Error in handwritten text extraction: {str(e)}")
            return ""

    def _post_process_text(self, text):
        """Post-process extracted text to improve quality."""
        if not text:
            return text

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Fix common OCR errors
        text = self._fix_common_ocr_errors(text)

        return text

    def _fix_common_ocr_errors(self, text):
        """Fix common OCR recognition errors with enhanced corrections."""
        if not text:
            return text

        # Enhanced OCR error corrections
        corrections = {
            # Common character substitutions
            r'\$MANIA': 'OSMANIA',  # $ instead of O
            r'0SMANIA': 'OSMANIA',  # 0 instead of O
            r'OSMANLA': 'OSMANIA',  # L instead of I
            r'QSMANIA': 'OSMANIA',  # Q instead of O
            r'GQVERNMENT': 'GOVERNMENT',  # Q instead of O
            r'G0VERNMENT': 'GOVERNMENT',  # 0 instead of O
            r'GOVEMMENT': 'GOVERNMENT',  # Missing 'n'
            r'GOVERMENT': 'GOVERNMENT',  # Missing 'n'
            r'GOVENMENT': 'GOVERNMENT',  # Missing 'r'
            r'GQVT': 'GOVT',  # Q instead of O
            r'G0VT': 'GOVT',  # 0 instead of O

            # Roll number corrections
            r'\bRoII\b': 'Roll',    # II instead of ll
            r'\bRo11\b': 'Roll',    # 11 instead of ll
            r'\bRoll\s*N0\.': 'Roll No.',  # 0 instead of o
            r'\bRoll\s*N0\b': 'Roll No',  # 0 instead of o
            r'\bNo\.\s*(\d)': r'No. \1',  # Fix spacing after No.

            # Common word corrections
            r'\bTelangana\b': 'Telangana',  # Case correction
            r'\bTELANGANA\b': 'TELANGANA',  # Case correction
            r'\bScholarship\b': 'Scholarship',  # Case correction
            r'\bSCHOLARSHlP\b': 'SCHOLARSHIP',  # l instead of I
            r'\bApplicati0n\b': 'Application',  # 0 instead of o
            r'\bCertificate\b': 'Certificate',  # Case correction
            r'\bB0nafide\b': 'Bonafide',  # 0 instead of o
            r'\bBonaf1de\b': 'Bonafide',  # 1 instead of i
            r'\bRenew\b': 'Renewal',  # Incomplete word
            r'\bRenwal\b': 'Renewal',  # Missing 'e'
            r'\bRenewsi\b': 'Renewal',  # OCR garbled
            r'\bRenewai\b': 'Renewal',  # OCR garbled
            r'\bRenewal\b': 'Renewal',  # Ensure correct
            r'\bFresh\b': 'Fresh',  # Ensure correct
            r'\bFreash\b': 'Fresh',  # OCR garbled
            r'\bFres\b': 'Fresh',  # Incomplete

            # LE-specific OCR corrections
            r'\bBonaf1de\b': 'Bonafide',  # 1 instead of i
            r'\bBonaf1de\b': 'Bonafide',  # Common OCR error
            r'\bTechn1cal\b': 'Technical',  # 1 instead of i
            r'\bTechnical\b': 'Technical',  # Ensure correct
            r'\bEducat1on\b': 'Education',  # 1 instead of i
            r'\bEducation\b': 'Education',  # Ensure correct
            r'\bTra1ning\b': 'Training',  # 1 instead of i
            r'\bTraining\b': 'Training',  # Ensure correct
            r'\bPolytech\b': 'Polytechnic',  # Incomplete
            r'\bPolytechn1c\b': 'Polytechnic',  # 1 instead of i
            r'\bConsolidated\b': 'Consolidated',  # Ensure correct
            r'\bConsoI1dated\b': 'Consolidated',  # I instead of l
            r'\bMemorandum\b': 'Memorandum',  # Ensure correct
            r'\bMemorendum\b': 'Memorandum',  # Common misspelling
            r'\bTransfer\b': 'Transfer',  # Ensure correct
            r'\bTransfar\b': 'Transfer',  # OCR error
            r'\bCertificate\b': 'Certificate',  # Ensure correct
            r'\bCertif1cate\b': 'Certificate',  # 1 instead of i
            r'\bDiploma\b': 'Diploma',  # Ensure correct
            r'\bD1ploma\b': 'Diploma',  # 1 instead of i

            # Additional LE-specific corrections
            r'\bSBTET\b': 'SBTET',  # Ensure correct
            r'\bSBT3T\b': 'SBTET',  # 3 instead of E
            r'\bSBT£T\b': 'SBTET',  # £ instead of E
            r'\bCandidate\b': 'Candidate',  # Ensure correct
            r'\bCand1date\b': 'Candidate',  # 1 instead of i
            r'\bMarks\b': 'Marks',  # Ensure correct
            r'\bMar|<s\b': 'Marks',  # | and < instead of k
            r'\bResult\b': 'Result',  # Ensure correct
            r'\bResu|t\b': 'Result',  # | instead of l
            r'\bRecord\b': 'Record',  # Ensure correct
            r'\bRec0rd\b': 'Record',  # 0 instead of o
            r'\bGrades\b': 'Grades',  # Ensure correct
            r'\bGrad3s\b': 'Grades',  # 3 instead of e

            # CRITICAL KEYWORD CORRECTIONS
            # Acknowledgement corrections
            r'\bAbknawlead\b': 'Acknowledgement',  # Heavily garbled
            r'\bAcknowledgemenResult\b': 'Acknowledgement',  # Result suffix
            r'\bAcknowlead\b': 'Acknowledgement',  # Missing letters
            r'\bAcknoledge\b': 'Acknowledgement',  # Misspelled

            # Attendance corrections
            r'\bAltendanee\b': 'Attendance',  # Garbled attendance
            r'\bAttendanee\b': 'Attendance',  # Missing 'c'
            r'\bAtendance\b': 'Attendance',  # Missing 't'
            r'\bAttendence\b': 'Attendance',  # Wrong vowels

            # Percentage corrections
            r'\bpemcentager\b': 'percentage',  # Heavily garbled
            r'\bpercentager\b': 'percentage',  # Extra 'r'
            r'\bpercent\b': 'percent',  # Ensure correct

            # Department corrections
            r'\bDepartmenResult\b': 'Department',  # Result suffix
            r'\bDepartinenResult\b': 'Department',  # Garbled + Result
            r'\bDepartment\b': 'Department',  # Ensure correct

            # CRITICAL: Remove "Result" suffix from common words (rotation correction artifacts)
            r'\bGovernmenResult\b': 'Government',  # Government + Result
            r'\bStudenResult\b': 'Student',  # Student + Result
            r'\bReporResult\b': 'Report',  # Report + Result
            r'\bPosResult\b': 'Post',  # Post + Result
            r'\bApplicationResult\b': 'Application',  # Application + Result
            r'\bScholarshipResult\b': 'Scholarship',  # Scholarship + Result
            r'\bVerificationResult\b': 'Verification',  # Verification + Result
            r'\bMinorityResult\b': 'Minority',  # Minority + Result
            r'\bMatricResult\b': 'Matric',  # Matric + Result
            r'\bTelanganaResult\b': 'Telangana',  # Telangana + Result

            # Date and number corrections
            r'\b(\d{2})/(\d{2})/2O(\d{2})\b': r'\1/\2/20\3',  # O instead of 0 in year
            r'\b(\d{2})/(\d{2})/2o(\d{2})\b': r'\1/\2/20\3',  # o instead of 0 in year
            r'\b2O25\b': '2025',  # O instead of 0
            r'\b2o25\b': '2025',  # o instead of 0
            r'\b2O24\b': '2024',  # O instead of 0
            r'\b2o24\b': '2024',  # o instead of 0

            # Character boundary corrections
            r'\b1\b(?=\s*[A-Z])': 'I',  # 1 instead of I at word boundaries
            r'\b0\b(?=\s*[A-Z])': 'O',  # 0 instead of O at word boundaries
            r'\bl\b(?=\s*[A-Z])': 'I',  # l instead of I at word boundaries

            # Common punctuation fixes
            r'\.{2,}': '.',  # Multiple dots to single dot
            r'\s+\.': '.',  # Space before dot
            r'\.\s+': '. ',  # Ensure space after dot
            r':\s*(\w)': r': \1',  # Ensure space after colon

            # Aadhaar specific corrections
            r'\bAadhar\b': 'Aadhaar',  # Common misspelling
            r'\bAdhaar\b': 'Aadhaar',  # Common misspelling
            r'\bAadhaar\s*N0\.': 'Aadhaar No.',  # 0 instead of o
            r'\bAadhaar\s*Number': 'Aadhaar Number',

            # Gender corrections
            r'\bMaIe\b': 'Male',  # I instead of l
            r'\bFemaIe\b': 'Female',  # I instead of l

            # Common form field corrections
            r'\bName\s*0f\b': 'Name of',  # 0 instead of o
            r'\bDate\s*0f\b': 'Date of',  # 0 instead of o
            r'\bFather\'?s?\s*Name': "Father's Name",
            r'\bMother\'?s?\s*Name': "Mother's Name",

            # College/Institution corrections
            r'\bCoIIege\b': 'College',  # I instead of l
            r'\bUniversity\b': 'University',  # Case correction
            r'\bEngineering\b': 'Engineering',  # Case correction
            r'\bTechnology\b': 'Technology',  # Case correction

            # Course corrections
            r'\bComputer\s*Science\b': 'Computer Science',
            r'\bInformation\s*Technology\b': 'Information Technology',
            r'\bElectronics\b': 'Electronics',
            r'\bMechanical\b': 'Mechanical',
            r'\bCivil\b': 'Civil',
        }

        # Apply corrections
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Additional cleanup
        text = self._additional_text_cleanup(text)

        return text

    def _additional_text_cleanup(self, text):
        """Additional text cleanup and normalization."""
        if not text:
            return text

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Fix common spacing issues
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'([.,;:!?])\s*', r'\1 ', text)  # Ensure space after punctuation

        # Fix number formatting
        text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)  # Remove spaces within numbers
        text = re.sub(r'(\d)\s*-\s*(\d)', r'\1-\2', text)  # Fix hyphenated numbers

        # Fix common abbreviations
        text = re.sub(r'\bDr\s*\.?\s*', 'Dr. ', text)  # Doctor title
        text = re.sub(r'\bMr\s*\.?\s*', 'Mr. ', text)  # Mister title
        text = re.sub(r'\bMs\s*\.?\s*', 'Ms. ', text)  # Miss title

        # Clean up line breaks and excessive spacing
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize double line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)  # Limit multiple line breaks

        return text.strip()