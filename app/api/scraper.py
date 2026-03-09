from fastapi import APIRouter, Request, HTTPException
import pandas as pd
import uuid
from app.models.schemas import ScraperRequest, ScraperResponse, ScraperMcqRequest, ScraperMcqResponse
from app.services import scraper_service, mcq_service, dedup_service

router = APIRouter()

@router.post("/scraper-content", response_model=ScraperResponse)
async def scraper_content_endpoint(request: ScraperRequest):
    """
    Scrapes content from the provided URL.
    Returns the title and cleaned text content.
    """
    data = scraper_service.scrape_url(request.url)
    return ScraperResponse(
        url=data["url"],
        title=data["title"],
        content=data["content"]
    )

@router.post("/scraper-generate-mcq", response_model=ScraperMcqResponse)
async def scraper_generate_mcq_endpoint(request: Request, body: ScraperMcqRequest):
    """
    Generates MCQs from provided scraper content, removes duplicates, and returns a CSV.
    """
    if not body.content:
        raise HTTPException(status_code=400, detail="Content is empty")

    # 1. Generate MCQs
    # Using the text content to generate MCQs
    mcqs = mcq_service.generate_mcqs_from_text(
        text=body.content,
        total_questions=body.total_questions,
        difficulty=body.difficulty
    )
    
    if not mcqs:
        raise HTTPException(status_code=400, detail="Failed to generate MCQs from content")

    # 2. Convert to DataFrame
    rows = []
    for item in mcqs:
        row = {
            "Question": item.question,
            "Option A": item.options.get('a', ''),
            "Option B": item.options.get('b', ''),
            "Option C": item.options.get('c', ''),
            "Option D": item.options.get('d', ''),
            "Correct Answer": item.correct_answer
        }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # 3. Remove Duplicates & Save
    # Generate a unique prefix
    unique_id = uuid.uuid4().hex[:8]
    # Clean title for filename
    safe_title = "".join(c for c in body.title if c.isalnum() or c in (' ', '_', '-')).strip()
    safe_title = safe_title.replace(" ", "_")[:50]
    filename_prefix = f"scraper_{safe_title}_{unique_id}"
    
    # dedup_service.remove_semantic_duplicates handles fuzzy deduplication and saving
    result = dedup_service.remove_semantic_duplicates(df, filename_prefix)
    
    # 4. Return Response
    base_url = str(request.base_url).rstrip("/")
    csv_url = f"{base_url}/exports/{result['filename']}"
    
    return ScraperMcqResponse(
        original_mcqs=result['original_count'],
        unique_mcqs=result['cleaned_count'],
        csv_url=csv_url
    )
