from fastapi import APIRouter, HTTPException
import pandas as pd
from app.models.schemas import ExportCsvRequest, ExportCsvResponse
from app.utils import file_manager

router = APIRouter()

@router.post("/export-csv", response_model=ExportCsvResponse)
async def export_csv_endpoint(request: ExportCsvRequest):
    # 1. Read persisted MCQs
    try:
        mcq_list = file_manager.read_json(request.file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="MCQs not found for this file. Generate MCQs first.")
    
    if not mcq_list:
        raise HTTPException(status_code=400, detail="No MCQs to export.")
        
    # 2. Convert to DataFrame
    # Columns: Question, Option A, Option B, Option C, Option D, Correct Answer
    rows = []
    for item in mcq_list:
        row = {
            "Question": item['question'],
            "Option A": item['options'].get('a', ''),
            "Option B": item['options'].get('b', ''),
            "Option C": item['options'].get('c', ''),
            "Option D": item['options'].get('d', ''),
            "Correct Answer": item['correct_answer']
        }
        rows.append(row)
        
    df = pd.DataFrame(rows)
    
    # 3. Write CSV
    try:
        saved_path = file_manager.write_csv(request.file_id, df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create CSV: {str(e)}")
        
    # 4. Return URL
    # Assuming the saved_path is absolute, we need to extract the filename
    # The file is saved in app/storage/csv/{file_id}.csv
    filename = f"{request.file_id}.csv"
    download_url = f"/exports/{filename}"
    
    return ExportCsvResponse(csv_url=download_url)
