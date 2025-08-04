# document_processor.py

import fitz  # PyMuPDF for PDFs
import docx  # python-docx for Word documents
import pytesseract
from pdf2image import convert_from_path

def extract_text_from_pdf(file_path):
    """Extracts text from a PDF file."""
    try:
        with fitz.open(file_path) as doc:
            text = "".join(page.get_text() for page in doc)
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def extract_text_from_docx(file_path):
    """Extracts text from a DOCX file."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        return ""

def extract_text_from_image(file_path):
    """Extracts text from an image file using OCR."""
    try:
        # For multi-page PDFs as images, this handles the first page.
        # For single images, it works directly.
        images = convert_from_path(file_path)
        text = pytesseract.image_to_string(images[0])
        return text.strip()
    except Exception as e:
        print(f"Error extracting image text (OCR): {e}")
        return ""

def get_text_from_file(file_path, mime_type):
    """
    Dispatcher function to extract text based on the file's MIME type.
    """
    if mime_type == 'application/pdf':
        return extract_text_from_pdf(file_path)
    elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return extract_text_from_docx(file_path)
    elif mime_type.startswith('image/'):
        return extract_text_from_image(file_path)
    else:
        print(f"Unsupported file type for text extraction: {mime_type}")
        return None
