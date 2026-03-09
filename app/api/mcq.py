from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional, Literal
from app.models.schemas import AnswerKeyRequest, AnswerKeyResponse, McqRequest, McqResponse
from app.services import answer_randomizer, mcq_service, pdf_service, text_service
from app.utils import file_manager
from docx import Document
from io import BytesIO

router = APIRouter()

@router.post("/generate-answer-key", response_model=AnswerKeyResponse)
async def generate_answer_key_endpoint(request: AnswerKeyRequest):
    key = answer_randomizer.generate_answer_key(request.total_questions)
    return AnswerKeyResponse(answer_key=key)

@router.post("/generate-mcq", response_model=McqResponse)
async def generate_mcq_endpoint(request: McqRequest):
    try:
        text = file_manager.read_text(request.file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
        
    mcqs = mcq_service.generate_mcqs_from_text(
        text=text, 
        total_questions=request.total_questions,
        difficulty=request.difficulty
    )
    
    if not mcqs:
        raise HTTPException(status_code=400, detail="Could not generate MCQs from this text. Text might be too short.")

    mcq_dicts = [m.model_dump() for m in mcqs]
    file_manager.save_json(request.file_id, mcq_dicts)

    return McqResponse(mcqs=mcqs)


@router.post("/detailTopicMcq-generate", response_model=McqResponse)
async def detail_topic_mcq_generate(
    file: Optional[UploadFile] = File(None),
    content: Optional[str] = Form(None),
    total_questions: int = Form(25),
    difficulty: Literal["easy", "medium", "hard"] = Form("medium"),
):
    if not file and not content:
        raise HTTPException(status_code=400, detail="Either file or content must be provided.")

    base_text: Optional[str] = None

    if content and content.strip():
        base_text = text_service.normalize_text(content)
    elif file:
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        filename = file.filename or ""
        ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

        if ext == "pdf":
            try:
                pdf_service.validate_pdf_bytes(raw_bytes)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

            try:
                file_id, saved_path = file_manager.save_upload(raw_bytes, filename, kind="pdf")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save PDF: {str(e)}")

            try:
                text, _ = pdf_service.extract_text_and_pages(saved_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to extract text from PDF: {str(e)}")

            base_text = text_service.normalize_text(text)

        elif ext in {"txt", "md"}:
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_bytes.decode("latin-1", errors="ignore")
            base_text = text_service.normalize_text(text)

        elif ext == "docx":
            try:
                doc = Document(BytesIO(raw_bytes))
                paragraphs = [p.text for p in doc.paragraphs if p.text]
                text = "\n".join(paragraphs)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read DOCX file: {str(e)}")
            base_text = text_service.normalize_text(text)

        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, or TXT.")

    if not base_text or not base_text.strip():
        raise HTTPException(status_code=400, detail="No usable text content found to generate MCQs.")

    mcqs = mcq_service.generate_mcqs_from_text(
        text=base_text,
        total_questions=total_questions,
        difficulty=difficulty,
    )

    if not mcqs:
        raise HTTPException(status_code=400, detail="Could not generate MCQs from this content. It might be too short or not factual.")

    return McqResponse(mcqs=mcqs)
