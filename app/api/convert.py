from fastapi import APIRouter, HTTPException
from app.models.schemas import ConvertRequest, ConvertResponse
from app.utils import file_manager

router = APIRouter()

@router.post("/convert-text", response_model=ConvertResponse)
async def convert_text(request: ConvertRequest):
    file_id = request.file_id
    output_format = request.output_format

    # 1. Read existing extracted text
    try:
        text = file_manager.read_text(file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Text not found for file_id {file_id}. Please upload PDF first.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading text: {str(e)}")

    download_url = ""

    # 2. Handle formats
    if output_format == "txt":
        # The text file already exists in storage/text/{file_id}.txt
        # We serve it via the /files/text mount
        # Check if file exists is implicit via read_text, but to be sure:
        # (We already read it, so it exists)
        download_url = f"/files/text/{file_id}.txt"
    
    elif output_format == "doc":
        try:
            # Generate DOCX
            # saved_path returns absolute path, but we need the URL path
            # file_manager.write_docx saves to storage/docs/{file_id}.docx
            file_manager.write_docx(file_id, text)
            download_url = f"/files/docs/{file_id}.docx"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate DOCX: {str(e)}")

    return ConvertResponse(download_url=download_url)
