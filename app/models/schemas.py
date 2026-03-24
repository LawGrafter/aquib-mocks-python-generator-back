from typing import List, Literal, Dict, Optional
from pydantic import BaseModel, Field, field_validator

class UploadResponse(BaseModel):
    file_id: str
    pages: int
    text_length: int

class ConvertRequest(BaseModel):
    file_id: str = Field(..., min_length=1, description="The ID of the file to convert")
    output_format: Literal["txt", "doc"]

class ConvertResponse(BaseModel):
    download_url: str

class McqRequest(BaseModel):
    file_id: str = Field(..., min_length=1)
    total_questions: int = Field(25, ge=1, le=200)
    difficulty: Literal["easy", "medium", "hard"] = "medium"

class McqItem(BaseModel):
    question: str
    options: Dict[str, str]
    correct_answer: Literal["a", "b", "c", "d"]

class McqResponse(BaseModel):
    mcqs: List[McqItem]

class AnswerKeyRequest(BaseModel):
    total_questions: int

class AnswerKeyResponse(BaseModel):
    answer_key: str

class ExportCsvRequest(BaseModel):
    file_id: str = Field(..., min_length=1)

class ExportCsvResponse(BaseModel):
    csv_url: str

class MistakeAnalysisRequest(BaseModel):
    file_id: str = Field(..., description="File ID of the uploaded wrong answers file (txt/md/pdf)")

class MistakeAnalysisResponse(BaseModel):
    notes: List[str]
    mcqs: List[McqItem]

class MistakePdfResponse(BaseModel):
    download_url: str
    csv_url: str

class ResearchRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)

class ResearchResponse(BaseModel):
    notes: str
    csv_url: str
    pdf_url: str

class CleanCsvResponse(BaseModel):
    csv_url: str
    original_count: int
    cleaned_count: int
    removed_count: int

class ScraperRequest(BaseModel):
    url: str = Field(..., description="The URL of the webpage to scrape")

class ScraperResponse(BaseModel):
    url: str
    title: str
    content: str

class ScraperMcqRequest(BaseModel):
    url: str
    title: str
    content: str
    total_questions: int = Field(50, ge=1)
    difficulty: Literal["easy", "medium", "hard"] = "medium"

class ScraperMcqResponse(BaseModel):
    original_mcqs: int
    unique_mcqs: int
    csv_url: str

class ExamGenerationRequest(BaseModel):
    difficulty: Literal["easy", "moderate", "easy-to-moderate"] = Field(
        "moderate", 
        description="Easy: Simple facts. Moderate: Mixed types. Easy-to-Moderate: Deep one-liners (Concept + Application)."
    )

class ExamGenerationResponse(BaseModel):
    total_generated: int
    final_unique_count: int
    csv_url: str
    breakdown: Dict[str, int]

class CustomExamRequest(BaseModel):
    subject: str = Field(..., min_length=1, description="The main subject")
    topics: List[str] = Field(..., min_length=1, description="List of specific sub-topics")
    difficulty: Literal["easy", "moderate", "easy-to-moderate", "hard"] = "moderate"
    total_questions: int = Field(10, ge=1, le=500, description="Total number of questions to generate")

class CustomExamResponse(BaseModel):
    total_generated: int
    final_unique_count: int
    csv_url: str
    subject: str
    pdf_url_en: Optional[str] = None
    pdf_url_hi: Optional[str] = None

class ContentMakerResponse(BaseModel):
    pdf_url: str

class RapidPdfMcqResponse(BaseModel):
    total_generated: int
    csv_url: str
