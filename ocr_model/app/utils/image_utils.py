import os
import logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def preprocess_image(image_path, quality_level='auto'):
    """
    Enhanced preprocessing for better OCR results on low-quality images.

    Args:
        image_path: Path to the image file
        quality_level: 'auto', 'basic', 'enhanced', or 'aggressive'

    Returns:
        PIL.Image: Preprocessed image
    """
    try:
        # Open image
        #image = Image.open(image_path)
        original_image = image.copy()

                # If input is a path, open the image
        if isinstance(image_path, str):
            image = Image.open(image_path)
        # If input is already a PIL Image, use it directly
        elif isinstance(image_path, Image.Image):
            image = image_path
        else:
            raise ValueError("Unsupported image input type for preprocessing.")

        # Determine quality level automatically if needed
        if quality_level == 'auto':
            quality_level = _assess_image_quality(image)

        logger.info(f"Preprocessing image with quality level: {quality_level}")

        # Apply preprocessing based on quality level
        if quality_level == 'basic':
            image = _basic_preprocessing(image)
        elif quality_level == 'enhanced':
            image = _enhanced_preprocessing(image)
        elif quality_level == 'aggressive':
            image = _aggressive_preprocessing(image)
        else:
            image = _basic_preprocessing(image)

        return image

    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        # Return original image if preprocessing fails
        try:
            return Image.open(image_path)
        except:
            return original_image

def _assess_image_quality(image):
    """Assess image quality to determine preprocessing level."""
    try:
        # Convert to grayscale for analysis
        if image.mode != 'L':
            gray_image = image.convert('L')
        else:
            gray_image = image

        # Calculate image statistics
        width, height = image.size
        total_pixels = width * height

        # Check image size (low resolution indicator)
        if total_pixels < 500000:  # Less than 0.5MP
            return 'aggressive'
        elif total_pixels < 1000000:  # Less than 1MP
            return 'enhanced'

        # Calculate contrast (low contrast indicator)
        histogram = gray_image.histogram()
        contrast = _calculate_contrast_from_histogram(histogram)

        if contrast < 50:
            return 'aggressive'
        elif contrast < 100:
            return 'enhanced'

        return 'basic'

    except Exception as e:
        logger.warning(f"Error assessing image quality: {str(e)}")
        return 'enhanced'  # Default to enhanced for safety

def _calculate_contrast_from_histogram(histogram):
    """Calculate contrast measure from histogram."""
    try:
        # Simple contrast measure based on histogram spread
        total_pixels = sum(histogram)
        if total_pixels == 0:
            return 0

        # Find the range of intensities
        first_nonzero = next((i for i, count in enumerate(histogram) if count > 0), 0)
        last_nonzero = next((255 - i for i, count in enumerate(reversed(histogram)) if count > 0), 255)

        return last_nonzero - first_nonzero
    except:
        return 100  # Default moderate contrast

def _basic_preprocessing(image):
    """Basic preprocessing for good quality images."""
    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Slight contrast enhancement
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)

    # Light sharpening
    image = image.filter(ImageFilter.SHARPEN)

    return image

def _enhanced_preprocessing(image):
    """Enhanced preprocessing for medium quality images."""
    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Auto-contrast adjustment
    image = ImageOps.autocontrast(image, cutoff=2)

    # Noise reduction
    image = image.filter(ImageFilter.MedianFilter(size=3))

    # Contrast enhancement
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)

    # Brightness adjustment
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)

    # Sharpening
    image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

    return image

def _aggressive_preprocessing(image):
    """Aggressive preprocessing for low quality images and handwritten text."""
    # Convert to grayscale
    if image.mode != 'L':
        image = image.convert('L')

    # Resize if too small (upscaling for better OCR, especially important for handwritten text)
    width, height = image.size
    if width < 1500 or height < 1500:  # Higher threshold for handwritten text
        scale_factor = max(1500 / width, 1500 / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = image.resize((new_width, new_height), Image.LANCZOS)

    # Histogram equalization (auto-contrast with more aggressive settings)
    image = ImageOps.autocontrast(image, cutoff=3)  # Less aggressive cutoff for handwritten text

    # Multiple noise reduction passes for handwritten text
    image = image.filter(ImageFilter.MedianFilter(size=3))  # Smaller filter first
    image = _bilateral_filter_pil(image)
    image = image.filter(ImageFilter.MedianFilter(size=5))  # Larger filter second

    # Enhanced contrast for handwritten text
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)  # Higher contrast for handwritten text

    # Brightness adjustment
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.1)  # Slight brightness increase

    # Morphological operations to clean up text
    image = _morphological_operations_handwritten(image)

    # Strong sharpening for handwritten text
    image = image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=250, threshold=1))

    return image

def _morphological_operations_handwritten(image):
    """Apply morphological operations optimized for handwritten text."""
    try:
        # Convert to binary with adaptive threshold for handwritten text
        # Use Otsu's method simulation
        histogram = image.histogram()
        total_pixels = sum(histogram)

        # Calculate optimal threshold using Otsu's method approximation
        sum_total = sum(i * histogram[i] for i in range(256))
        sum_background = 0
        weight_background = 0
        max_variance = 0
        optimal_threshold = 128

        for threshold in range(256):
            weight_background += histogram[threshold]
            if weight_background == 0:
                continue

            weight_foreground = total_pixels - weight_background
            if weight_foreground == 0:
                break

            sum_background += threshold * histogram[threshold]
            mean_background = sum_background / weight_background
            mean_foreground = (sum_total - sum_background) / weight_foreground

            variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2

            if variance > max_variance:
                max_variance = variance
                optimal_threshold = threshold

        # Apply adaptive threshold
        binary_image = image.point(lambda x: 255 if x > optimal_threshold else 0, mode='1')

        # Convert back to grayscale
        image = binary_image.convert('L')

        # Light morphological operations for handwritten text (preserve character structure)
        image = image.filter(ImageFilter.MinFilter(2))  # Light erosion
        image = image.filter(ImageFilter.MaxFilter(2))  # Light dilation

        return image
    except:
        return image

def _bilateral_filter_pil(image):
    """Simulate bilateral filtering using PIL operations."""
    try:
        # Apply multiple passes of median filter with different sizes
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = image.filter(ImageFilter.SMOOTH)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        return image
    except:
        return image

def _morphological_operations(image):
    """Apply morphological operations to clean up text."""
    try:
        # Convert to binary for morphological operations
        threshold = 128
        binary_image = image.point(lambda x: 255 if x > threshold else 0, mode='1')

        # Convert back to grayscale
        image = binary_image.convert('L')

        # Apply erosion followed by dilation (opening) to remove noise
        image = image.filter(ImageFilter.MinFilter(3))  # Erosion
        image = image.filter(ImageFilter.MaxFilter(3))  # Dilation

        return image
    except:
        return image

def save_preprocessed_image(image_path, output_dir=None):
    """
    Preprocess image and save the result.

    Args:
        image_path: Path to the image file
        output_dir: Directory to save the preprocessed image (default: same as input)

    Returns:
        str: Path to the preprocessed image
    """
    try:
        # Preprocess image
        preprocessed = preprocess_image(image_path)

        # Determine output path
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.basename(image_path)
            output_path = os.path.join(output_dir, f"preprocessed_{filename}")
        else:
            directory = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(directory, f"{name}_preprocessed{ext}")

        # Save preprocessed image
        preprocessed.save(output_path)

        return output_path

    except Exception as e:
        logger.error(f"Error saving preprocessed image: {str(e)}")
        return image_path  # Return original path if saving fails
