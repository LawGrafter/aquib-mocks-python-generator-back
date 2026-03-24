import os
import shutil
import uuid
import json
from pathlib import Path
from typing import Dict
import pandas as pd
from docx import Document

# Get storage root from env or default
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "app/storage")

# Define subdirectory names
DIR_PDFS = "pdfs"
DIR_TEXT = "text"
DIR_DOCS = "docs"
DIR_CSV = "csv"
DIR_JSON = "json"

def get_storage_paths() -> Dict[str, Path]:
    """
    Returns a dictionary of pathlib.Path objects for each storage category.
    Ensures directories exist.
    """
    root = Path(STORAGE_ROOT)
    paths = {
        "root": root,
        "pdfs": root / DIR_PDFS,
        "text": root / DIR_TEXT,
        "docs": root / DIR_DOCS,
        "csv": root / DIR_CSV,
        "json": root / DIR_JSON,
    }
    
    # Create directories if they don't exist
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
        
    return paths

# Initialize directories on module load (or call this explicitly in main startup)
# Calling it here ensures they exist whenever this module is imported/used
get_storage_paths()

def safe_join(directory: Path, filename: str) -> Path:
    """
    Safely join a directory and a filename, preventing directory traversal.
    """
    # Simple check for traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        # In a real scenario, use os.path.normpath and check commonprefix, 
        # but since we generate filenames with UUIDs, strict validation is usually okay.
        # However, for safety:
        cleaned = os.path.basename(filename)
        return directory / cleaned
    return directory / filename

def save_upload(file_bytes: bytes, original_filename: str, kind: str = "pdf") -> tuple[str, str]:
    """
    Saves uploaded bytes to the appropriate directory.
    Returns (file_id, saved_path_str).
    """
    file_id = str(uuid.uuid4())
    paths = get_storage_paths()
    
    if kind == "pdf":
        target_dir = paths["pdfs"]
        ext = ".pdf"
    else:
        # Default or extendable
        target_dir = paths["root"]
        ext = os.path.splitext(original_filename)[1]

    filename = f"{file_id}{ext}"
    saved_path = target_dir / filename
    
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
        
    return file_id, str(saved_path)

def write_text(file_id: str, text: str, ext: str = "txt") -> str:
    """
    Writes text content to a file in the text directory.
    Returns saved_path_str.
    """
    paths = get_storage_paths()
    filename = f"{file_id}.{ext}"
    saved_path = paths["text"] / filename
    
    with open(saved_path, "w", encoding="utf-8") as f:
        f.write(text)
        
    return str(saved_path)

def save_generated_pdf(pdf_buffer, filename: str) -> str:
    """
    Saves a PDF buffer to the docs directory.
    Returns the relative path for the URL (e.g., 'filename.pdf').
    """
    paths = get_storage_paths()
    # Ensure filename ends with .pdf
    if not filename.endswith('.pdf'):
        filename += '.pdf'
        
    saved_path = paths["docs"] / filename
    
    with open(saved_path, "wb") as f:
        f.write(pdf_buffer.getvalue())
        
    return filename

def write_docx(file_id: str, text: str) -> str:
    """
    Writes text content to a .docx file in the docs directory.
    Returns saved_path_str.
    """
    paths = get_storage_paths()
    filename = f"{file_id}.docx"
    saved_path = paths["docs"] / filename
    
    doc = Document()
    doc.add_paragraph(text)
    doc.save(saved_path)
    
    return str(saved_path)

def write_csv(file_id: str, df: pd.DataFrame) -> str:
    """
    Writes a pandas DataFrame to a .csv file in the csv directory.
    Returns saved_path_str.
    """
    paths = get_storage_paths()
    filename = f"{file_id}.csv"
    saved_path = paths["csv"] / filename
    
    df.to_csv(saved_path, index=False, encoding="utf-8-sig")
    
    return str(saved_path)

def read_text(file_id: str) -> str:
    """
    Reads text from the text directory given a file_id.
    Assumes .txt extension by default for reading extracted text.
    """
    paths = get_storage_paths()
    # Try .txt first
    filename = f"{file_id}.txt"
    file_path = paths["text"] / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Text file for ID {file_id} not found.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def save_json(file_id: str, data: list) -> str:
    """
    Saves list of dicts (MCQs) to JSON file.
    Returns saved_path_str.
    """
    paths = get_storage_paths()
    filename = f"{file_id}_mcqs.json"
    saved_path = paths["json"] / filename
    
    with open(saved_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return str(saved_path)

def read_json(file_id: str) -> list:
    """
    Reads JSON data from file.
    """
    paths = get_storage_paths()
    filename = f"{file_id}_mcqs.json"
    file_path = paths["json"] / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found for ID: {file_id}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
