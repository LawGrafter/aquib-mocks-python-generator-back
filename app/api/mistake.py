from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from app.models.schemas import MistakeAnalysisRequest, MistakeAnalysisResponse, MistakePdfResponse
from app.services import mistake_service
from app.utils import file_manager
import shutil
import uuid

router = APIRouter()

import pandas as pd

@router.post("/analyze-mistakes/pdf", response_model=MistakePdfResponse)
async def analyze_mistakes_pdf(request: Request, file: UploadFile = File(...)):
    """
    Uploads a file, generates a PDF report, saves it, and returns a download URL.
    Also returns a CSV download URL for the generated MCQs.
    """
    try:
        content = await file.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
            
        if not text:
            raise HTTPException(status_code=400, detail="File is empty")

        # Process with AI
        result = mistake_service.analyze_mistakes_with_ai(text)
        
        if not result:
            raise HTTPException(status_code=500, detail="AI processing failed")

        # Generate PDF Buffer
        pdf_buffer = mistake_service.generate_mistake_pdf(result["notes"], result["mcqs"])
        
        # Unique ID for this transaction
        unique_id = uuid.uuid4().hex[:8]
        
        # Save PDF to disk
        pdf_filename = f"mistake_analysis_{unique_id}.pdf"
        file_manager.save_generated_pdf(pdf_buffer, pdf_filename)
        
        # Generate CSV for MCQs
        csv_filename = f"mistake_mcqs_{unique_id}" # write_csv adds .csv
        
        # Transform MCQs to DataFrame
        mcq_data = []
        for mcq in result["mcqs"]:
            row = {
                "Question": mcq.question,
                "Option A": mcq.options.get("a", ""),
                "Option B": mcq.options.get("b", ""),
                "Option C": mcq.options.get("c", ""),
                "Option D": mcq.options.get("d", ""),
                "Correct Answer": mcq.correct_answer
            }
            mcq_data.append(row)
            
        if mcq_data:
            df = pd.DataFrame(mcq_data)
            file_manager.write_csv(csv_filename, df)
            csv_download_url = f"{str(request.base_url).rstrip('/')}/exports/{csv_filename}.csv"
        else:
            csv_download_url = ""
        
        # Construct PDF Download URL
        base_url = str(request.base_url).rstrip("/")
        download_url = f"{base_url}/files/docs/{pdf_filename}"
        
        return MistakePdfResponse(
            download_url=download_url,
            csv_url=csv_download_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")

@router.post("/analyze-mistakes-upload", response_model=MistakeAnalysisResponse)
async def analyze_mistakes_upload(file: UploadFile = File(...)):
    """
    Directly upload a text/markdown file for mistake analysis.
    """
    try:
        content = await file.read()
        # Decode bytes to string
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1 if utf-8 fails
            text = content.decode("latin-1")
            
        if not text:
            raise HTTPException(status_code=400, detail="File is empty")
            
        # Optional: Save it for record keeping (using a temp file_id)
        # file_id = str(uuid.uuid4())
        # file_manager.write_text(file_id, text)

        # Process with AI
        result = mistake_service.analyze_mistakes_with_ai(text)
        
        if not result:
            raise HTTPException(status_code=500, detail="AI processing failed")

        return MistakeAnalysisResponse(
            notes=result["notes"],
            mcqs=result["mcqs"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/analyze-mistakes", response_model=MistakeAnalysisResponse)
async def analyze_mistakes_endpoint(request: MistakeAnalysisRequest):
    # 1. Read the file content
    try:
        text = file_manager.read_text(request.file_id)
    except FileNotFoundError:
        # Fallback: Check if user provided a raw path (for local dev convenience)
        # In a real app, strictly use file_id, but here we support the user's specific workflow.
        import os
        if os.path.exists(request.file_id):
             with open(request.file_id, "r", encoding="utf-8") as f:
                 text = f.read()
        else:
            raise HTTPException(status_code=404, detail="File not found")

    if not text:
        raise HTTPException(status_code=400, detail="File is empty")

    # 2. Process with AI
    result = mistake_service.analyze_mistakes_with_ai(text)
    
    if not result:
        raise HTTPException(status_code=500, detail="AI processing failed")

    return MistakeAnalysisResponse(
        notes=result["notes"],
        mcqs=result["mcqs"]
    )
