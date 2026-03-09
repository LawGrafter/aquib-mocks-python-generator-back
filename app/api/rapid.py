from fastapi import APIRouter, HTTPException, UploadFile, File
import pandas as pd
import uuid
from app.models.schemas import RapidPdfMcqResponse
from app.services import pdf_service, text_service, mcq_service
from app.utils.file_manager import write_csv, save_upload

router = APIRouter()

@router.post("/rapidpdfmcq", response_model=RapidPdfMcqResponse)
async def rapid_pdf_mcq(file: UploadFile = File(...)):
    """
    Rapidly generates 25 MCQs from an uploaded PDF and returns a CSV download URL.
    """
    try:
        # 1. Read and Validate PDF
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")
            
        try:
            pdf_service.validate_pdf_bytes(content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        # 2. Save PDF (Temporary or Persistent)
        # We need to save it to extract text using pymupdf (fitz) which prefers file paths
        file_id, saved_path = save_upload(content, file.filename or "upload.pdf", kind="pdf")
        
        # 3. Extract Text
        try:
            text, _ = pdf_service.extract_text_and_pages(saved_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")
            
        normalized_text = text_service.normalize_text(text)
        if not normalized_text:
             raise HTTPException(status_code=400, detail="Could not extract usable text from PDF")

        # 4. Generate MCQs (25 questions)
        # We use the existing mcq_service.generate_mcqs_from_text
        # It handles chunking and Gemini calls.
        mcqs = mcq_service.generate_mcqs_from_text(
            text=normalized_text, 
            total_questions=25, 
            difficulty="moderate" # Default to moderate as per general requirement
        )
        
        if not mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate MCQs from text")
            
        # 5. Format to CSV
        data = []
        for i, mcq in enumerate(mcqs, 1):
            row = {
                "Question": mcq.question,
                "Option A": mcq.options.get("a", ""),
                "Option B": mcq.options.get("b", ""),
                "Option C": mcq.options.get("c", ""),
                "Option D": mcq.options.get("d", ""),
                "Correct Answer": mcq.correct_answer.lower() # Normalize to lowercase a,b,c,d
            }
            data.append(row)
            
        df = pd.DataFrame(data)
        
        # 6. Save CSV
        filename_prefix = f"rapid_mcq_{uuid.uuid4().hex[:8]}"
        write_csv(filename_prefix, df)
        csv_filename = f"{filename_prefix}.csv"
        
        # 7. Return Response
        csv_url = f"/exports/{csv_filename}"
        
        return RapidPdfMcqResponse(
            total_generated=len(df),
            csv_url=csv_url
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
