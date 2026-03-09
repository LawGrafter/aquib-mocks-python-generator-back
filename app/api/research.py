from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from typing import List
from app.models.schemas import ResearchRequest, ResearchResponse, ContentMakerResponse
from app.services.research_service import (
    generate_research_content,
    save_research_csv,
    save_research_pdf,
    generate_notes_from_text,
)
from app.services import pdf_service, text_service
from app.utils import file_manager
import uuid

router = APIRouter()

@router.post("/research", response_model=ResearchResponse)
async def research_topic(request: Request, body: ResearchRequest):
    """
    Research a topic: Generates comprehensive notes (PDF) and 50 MCQs (CSV).
    """
    try:
        # Generate unique ID for this request
        unique_id = uuid.uuid4().hex[:8]
        filename_prefix = f"research_{body.subject}_{body.topic}_{unique_id}".replace(" ", "_")

        # 1. Generate Content (Notes + MCQs)
        content = generate_research_content(body.subject, body.topic)
        
        notes = content.get("notes", "No notes generated.")
        mcqs = content.get("mcqs", [])

        if not mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate MCQs.")

        # 2. Save MCQs to CSV
        csv_filename = save_research_csv(mcqs, filename_prefix)
        
        # 3. Save Notes to PDF
        pdf_filename = save_research_pdf(notes, body.subject, body.topic, filename_prefix)
        
        # 4. Construct URLs
        base_url = str(request.base_url).rstrip("/")
        csv_url = f"{base_url}/exports/{csv_filename}"
        pdf_url = f"{base_url}/files/docs/{pdf_filename}"

        return ResearchResponse(
            notes=notes,
            csv_url=csv_url,
            pdf_url=pdf_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contentmaker", response_model=ContentMakerResponse)
async def contentmaker(
    request: Request,
    files: List[UploadFile] = File(...),
    topic: str | None = None,
):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="At least one PDF file is required.")

        combined_text_parts: List[str] = []

        for file in files:
            content = await file.read()
            if not content:
                continue

            try:
                pdf_service.validate_pdf_bytes(content)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")

            try:
                file_id, saved_path = file_manager.save_upload(content, file.filename, kind="pdf")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save file {file.filename}: {str(e)}")

            try:
                text, _ = pdf_service.extract_text_and_pages(saved_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to extract text from {file.filename}: {str(e)}")

            normalized = text_service.normalize_text(text)
            if normalized:
                combined_text_parts.append(normalized)

        if not combined_text_parts:
            raise HTTPException(status_code=400, detail="No usable text content found in uploaded PDFs.")

        combined_text = "\n\n".join(combined_text_parts)

        notes = generate_notes_from_text(combined_text, topic)
        if not notes:
            raise HTTPException(status_code=500, detail="Failed to generate notes from content.")

        unique_id = uuid.uuid4().hex[:8]
        filename_prefix = f"contentmaker_notes_{unique_id}"

        pdf_filename = save_research_pdf(notes, "Custom Content", "Compiled PDFs", filename_prefix)

        base_url = str(request.base_url).rstrip("/")
        pdf_url = f"{base_url}/files/docs/{pdf_filename}"

        return ContentMakerResponse(pdf_url=pdf_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rapidstenocontent", response_model=ContentMakerResponse)
async def rapid_steno_content(
    request: Request,
    files: List[UploadFile] = File(...),
    topic: str | None = None,
):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="At least one PDF file is required.")

        combined_text_parts: List[str] = []

        for file in files:
            content = await file.read()
            if not content:
                continue

            try:
                pdf_service.validate_pdf_bytes(content)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"{file.filename}: {str(e)}")

            try:
                _, saved_path = file_manager.save_upload(content, file.filename, kind="pdf")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to save file {file.filename}: {str(e)}")

            try:
                text, _ = pdf_service.extract_text_and_pages(saved_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to extract text from {file.filename}: {str(e)}")

            normalized = text_service.normalize_text(text)
            if normalized:
                combined_text_parts.append(normalized)

        if not combined_text_parts:
            raise HTTPException(status_code=400, detail="No usable text content found in uploaded PDFs.")

        combined_text = "\n\n".join(combined_text_parts)

        notes = generate_notes_from_text(combined_text, topic)
        if not notes:
            raise HTTPException(status_code=500, detail="Failed to generate notes from content.")

        unique_id = uuid.uuid4().hex[:8]
        filename_prefix = f"rapidsteno_notes_{unique_id}"

        pdf_title_topic = topic or "Compiled PDFs"
        pdf_filename = save_research_pdf(notes, "RapidSteno Content", pdf_title_topic, filename_prefix)

        base_url = str(request.base_url).rstrip("/")
        pdf_url = f"{base_url}/files/docs/{pdf_filename}"

        return ContentMakerResponse(pdf_url=pdf_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
