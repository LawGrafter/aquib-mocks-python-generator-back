from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from app.models.schemas import CleanCsvResponse
from app.services.dedup_service import remove_semantic_duplicates
import uuid
import pandas as pd
from io import BytesIO

router = APIRouter()

@router.post("/clean/remove-duplicates", response_model=CleanCsvResponse)
async def remove_duplicates(request: Request, file: UploadFile = File(...)):
    """
    Upload a CSV file. The API will use AI to detect and remove semantically duplicate questions.
    Returns a URL to download the cleaned CSV.
    """
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV.")

    try:
        # Read file into DataFrame
        contents = await file.read()
        df = pd.read_csv(BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty.")

        # Generate unique prefix
        unique_id = uuid.uuid4().hex[:8]
        filename_prefix = f"cleaned_{unique_id}"

        # Process
        result = remove_semantic_duplicates(df, filename_prefix)
        
        # Construct URL
        base_url = str(request.base_url).rstrip("/")
        csv_url = f"{base_url}/exports/{result['filename']}"

        return CleanCsvResponse(
            csv_url=csv_url,
            original_count=result['original_count'],
            cleaned_count=result['cleaned_count'],
            removed_count=result['removed_count']
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
