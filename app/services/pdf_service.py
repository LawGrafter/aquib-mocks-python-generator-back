import fitz  # PyMuPDF
from pathlib import Path

def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    """
    Validates if the provided bytes constitute a valid PDF.
    Raises ValueError if invalid or empty.
    """
    if not pdf_bytes:
        raise ValueError("File is empty")
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count < 1:
             raise ValueError("PDF has no pages")
        doc.close()
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {str(e)}")

def extract_text_and_pages(pdf_path: str) -> tuple[str, int]:
    """
    Extracts text and page count from a PDF file.
    Returns (text, page_count).
    """
    path_obj = Path(pdf_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        
        if doc.is_encrypted:
            # Try to decrypt with empty password
            if not doc.authenticate(""):
                raise ValueError("PDF is encrypted and cannot be opened")
                
        text_content = []
        for page in doc:
            text_content.append(page.get_text())
            
        # Join with a special delimiter to preserve page boundaries
        full_text = "\n<<<PAGE_BREAK>>>\n".join(text_content)
        pages = doc.page_count
        doc.close()
        
        return full_text, pages
        
    except Exception as e:
        # Re-raise known errors, wrap others
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise e
        raise RuntimeError(f"Failed to process PDF: {str(e)}")
