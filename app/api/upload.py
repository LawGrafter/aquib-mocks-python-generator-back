import os
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.utils import file_manager
from app.services import pdf_service, text_service
from app.models.schemas import UploadResponse

router = APIRouter()

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 15))

@router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    # 1. Validate file size (approximation via spool, real check requires reading)
    # FastAPI UploadFile is spooled. We can check file.size if available (some versions)
    # or read content.
    
    # Read file content
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file")

    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Max size is {MAX_UPLOAD_MB}MB"
        )

    # 2. Validate PDF format
    try:
        pdf_service.validate_pdf_bytes(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Save PDF
    try:
        file_id, saved_path = file_manager.save_upload(content, file.filename, kind="pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 4. Extract Text
    try:
        text, pages = pdf_service.extract_text_and_pages(saved_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # 5. Normalize Text
    normalized_text = text_service.normalize_text(text)
    
    # 6. Save Text
    try:
        file_manager.write_text(file_id, normalized_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save extracted text: {str(e)}")

    return UploadResponse(
        file_id=file_id,
        pages=pages,
        text_length=len(normalized_text)
    )
