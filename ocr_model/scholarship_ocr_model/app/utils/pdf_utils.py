import os
import subprocess
import tempfile
import logging
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_pdf_to_images(pdf_path, dpi=300, quality_mode='auto'):
    """
    Convert PDF to images using Poppler's pdftoppm with enhanced quality options.

    Args:
        pdf_path: Path to the PDF file
        dpi: DPI for the output images (default: 300)
        quality_mode: 'auto', 'standard', 'high', or 'ultra' for different quality levels

    Returns:
        list: Paths to the generated image files
    """
    try:
        # Determine optimal DPI based on quality mode
        if quality_mode == 'auto':
            quality_mode = _assess_pdf_quality(pdf_path)

        # Adjust DPI based on quality mode
        if quality_mode == 'ultra':
            dpi = max(dpi, 600)  # Ultra high quality
        elif quality_mode == 'high':
            dpi = max(dpi, 450)  # High quality
        elif quality_mode == 'standard':
            dpi = max(dpi, 300)  # Standard quality

        logger.info(f"Converting PDF with quality mode: {quality_mode}, DPI: {dpi}")

        # Create temporary directory for output images
        with tempfile.TemporaryDirectory() as temp_dir:
            # Base filename for output images
            output_base = os.path.join(temp_dir, "page")

            # Determine pdftoppm command based on platform
            system = platform.system()

            # Build command with enhanced options
            base_cmd = []
            if system == "Windows":
                base_cmd = ["pdftoppm"]
            else:
                base_cmd = ["/usr/bin/pdftoppm"]

            # Enhanced command options for better quality
            cmd = base_cmd + [
                "-png",                    # PNG format for better quality
                "-r", str(dpi),           # Resolution
                "-aa", "yes",             # Enable anti-aliasing
                "-aaVector", "yes",       # Anti-aliasing for vector graphics
                "-freetype", "yes",       # Use FreeType for better font rendering
                pdf_path,
                output_base
            ]

            # Add quality-specific options
            if quality_mode in ['high', 'ultra']:
                cmd.insert(-2, "-cropbox")  # Use crop box for better margins

            if quality_mode == 'ultra':
                cmd.insert(-2, "-thinlinemode")  # Better thin line rendering
                cmd.insert(-2, "solid")

            # Execute command
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"pdftoppm failed: {result.stderr}")

                # Try alternative approach for Windows if first attempt failed
                if system == "Windows":
                    logger.info("Trying alternative approach for Windows...")
                    # Try with full path if installed via Chocolatey
                    cmd[0] = r"C:\Program Files\poppler\bin\pdftoppm.exe"
                    logger.info(f"Running command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        logger.error(f"Alternative approach failed: {result.stderr}")
                        return []

            # Get list of generated image files
            image_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.png')]

            # Sort files by page number
            image_files.sort()

            # Copy files to a non-temporary location
            output_files = []
            for i, img_path in enumerate(image_files):
                # Create output directory in same location as PDF
                output_dir = os.path.join(os.path.dirname(pdf_path), "pdf_images")
                os.makedirs(output_dir, exist_ok=True)

                # Output path
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_path = os.path.join(output_dir, f"{pdf_name}_page_{i+1}.png")

                # Copy file
                with open(img_path, 'rb') as src, open(output_path, 'wb') as dst:
                    dst.write(src.read())

                output_files.append(output_path)

            return output_files

    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        return []

def _assess_pdf_quality(pdf_path):
    """Assess PDF quality to determine optimal conversion settings."""
    try:
        # Get file size as a rough indicator
        file_size = os.path.getsize(pdf_path)

        # Small files might be low quality scans
        if file_size < 500000:  # Less than 500KB
            return 'ultra'
        elif file_size < 2000000:  # Less than 2MB
            return 'high'
        else:
            return 'standard'

    except Exception as e:
        logger.warning(f"Error assessing PDF quality: {str(e)}")
        return 'high'  # Default to high quality

def convert_pdf_to_images_with_fallback(pdf_path, max_attempts=3):
    """
    Convert PDF to images with multiple fallback strategies for problematic PDFs.

    Args:
        pdf_path: Path to the PDF file
        max_attempts: Maximum number of conversion attempts with different strategies

    Returns:
        list: Paths to the generated image files
    """
    # OPTIMIZED: Start with faster, lower DPI strategies
    strategies = [
        {'dpi': 200, 'quality_mode': 'standard'},  # Fast first attempt
        {'dpi': 300, 'quality_mode': 'standard'},  # Standard quality
        {'dpi': 450, 'quality_mode': 'high'}       # High quality only if needed
    ]

    for attempt, strategy in enumerate(strategies[:max_attempts], 1):
        logger.info(f"PDF conversion attempt {attempt}/{max_attempts} with strategy: {strategy}")

        try:
            result = convert_pdf_to_images(
                pdf_path,
                dpi=strategy['dpi'],
                quality_mode=strategy['quality_mode']
            )

            if result:  # If successful, return result
                logger.info(f"PDF conversion successful on attempt {attempt}")
                return result

        except Exception as e:
            logger.warning(f"PDF conversion attempt {attempt} failed: {str(e)}")
            continue

    logger.error(f"All PDF conversion attempts failed for: {pdf_path}")
    return []

def enhance_pdf_image_quality(image_path):
    """
    Apply additional enhancement specifically for PDF-converted images.

    Args:
        image_path: Path to the image converted from PDF

    Returns:
        PIL.Image: Enhanced image
    """
    try:
        from .image_utils import preprocess_image

        # Use aggressive preprocessing for PDF images (often lower quality)
        enhanced_image = preprocess_image(image_path, quality_level='enhanced')

        return enhanced_image

    except Exception as e:
        logger.error(f"Error enhancing PDF image: {str(e)}")
        # Return original image if enhancement fails
        from PIL import Image
        return Image.open(image_path)
