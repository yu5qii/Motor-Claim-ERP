import io
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pypdf import PdfReader
from pdf2image import convert_from_bytes

# IMPORTANT: If you are on Windows, uncomment and update this line to your Tesseract path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_image_for_ocr(pil_image):
    """Uses OpenCV to clean up the invoice image for better OCR accuracy."""
    open_cv_image = np.array(pil_image)
    
    # Convert RGB to BGR 
    if len(open_cv_image.shape) == 3:
        open_cv_image = open_cv_image[:, :, ::-1].copy() 
    
    # Convert to grayscale
    gray = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)
    
    # Apply binary thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    return thresh

def process_image(uploaded_file):
    """Extracts text from raw image uploads (PNG, JPG)."""
    image = Image.open(uploaded_file)
    processed_img = preprocess_image_for_ocr(image)
    text = pytesseract.image_to_string(processed_img)
    return text, 1

def pdf_text(uploaded_file):
    """Attempts native text extraction, falls back to OCR for scanned PDFs."""
    data = uploaded_file.getvalue()
    
    reader = PdfReader(io.BytesIO(data))
    text_content = []
    has_text = False
    
    for p in reader.pages:
        page_text = p.extract_text() or ""
        if page_text.strip():
            has_text = True
        text_content.append(page_text)
        
    combined_text = "\n".join(text_content)
    
    if not has_text:
        # Note: on Windows, you may need to add poppler_path=r'C:\path\to\poppler\bin' 
        # to the convert_from_bytes arguments.
        pages = convert_from_bytes(data)
        ocr_text = []
        
        for page in pages:
            processed_img = preprocess_image_for_ocr(page)
            ocr_text.append(pytesseract.image_to_string(processed_img))
            
        return "\n".join(ocr_text), len(pages)
        
    return combined_text, len(reader.pages)