Phase 0 — Project Bootstrap (create structure + dependencies)

PROMPT (paste in code editor AI):

You are a senior Python backend architect. Create a production-ready FastAPI project skeleton for a PDF→Text→MCQ→CSV backend.

Requirements:
- Python 3.11+
- FastAPI + Uvicorn
- Pydantic
- PyMuPDF (fitz) (preferred) but keep pdfplumber optional
- python-docx
- pandas
- UUID file handling
- Environment variables via python-dotenv
- Logging

Deliver:
1) Folder structure exactly:
app/
 ├── main.py
 ├── api/
 │   ├── upload.py
 │   ├── convert.py
 │   ├── mcq.py
 │   └── export.py
 ├── services/
 │   ├── pdf_service.py
 │   ├── text_service.py
 │   ├── mcq_service.py
 │   └── answer_randomizer.py
 ├── models/
 │   └── schemas.py
 ├── utils/
 │   └── file_manager.py
 └── storage/
     ├── pdfs/
     ├── text/
     ├── docs/
     └── csv/

2) Add:
- requirements.txt (or pyproject) with pinned-ish versions
- .env.example with STORAGE_ROOT, MAX_UPLOAD_MB, LOG_LEVEL

3) Provide a minimal main.py that mounts routers and serves static downloads from /files and /exports.

Do not implement endpoints yet; just create scaffolding + config + logging.
Return file contents for every file created.


✅ After Phase 0, run:

pip install -r requirements.txt
uvicorn app.main:app --reload

Phase 1 — File Manager + Schemas (foundation)

PROMPT:

Implement the foundation layer.

Create/Update these files with full code:

1) app/utils/file_manager.py
- Must create directories on startup (pdfs/text/docs/csv)
- Functions:
  - get_storage_paths() -> dict paths
  - save_upload(file_bytes, original_filename, kind="pdf") -> (file_id, saved_path)
  - write_text(file_id, text, ext="txt") -> saved_path
  - write_docx(file_id, text) -> saved_path
  - write_csv(file_id, df) -> saved_path
  - read_text(file_id) -> str
  - safe_join(root, *parts) protections
- Use UUID4 for file_id.
- No hard-coded absolute paths; use env STORAGE_ROOT default "app/storage".

2) app/models/schemas.py
- Pydantic models:
  - UploadResponse(file_id: str, pages: int, text_length: int)
  - ConvertRequest(file_id: str, output_format: Literal["txt","doc"])
  - ConvertResponse(download_url: str)
  - McqRequest(file_id: str, total_questions: int=25, difficulty: Literal["easy","medium","hard"]="medium")
  - McqItem(question: str, options: dict[str,str], correct_answer: Literal["a","b","c","d"])
  - McqResponse(mcqs: list[McqItem])
  - AnswerKeyRequest(total_questions: int)
  - AnswerKeyResponse(answer_key: str)
  - ExportCsvRequest(file_id: str)
  - ExportCsvResponse(csv_url: str)
- Add validation: total_questions min 1 max 200; file_id non-empty

Return complete code.


✅ Quick check: start server, ensure no import errors.

Phase 2 — PDF Extraction Service + Upload API

PROMPT:

Implement PDF upload + extraction.

Create/Update files:

1) app/services/pdf_service.py
- Use PyMuPDF (fitz)
- Functions:
  - validate_pdf_bytes(pdf_bytes) -> None raises ValueError
  - extract_text_and_pages(pdf_path) -> (text: str, pages: int)
- Must handle encrypted/empty PDFs gracefully with clear errors.

2) app/services/text_service.py
- Simple functions:
  - normalize_text(text) (remove extra spaces, fix newlines)
  - chunk_text(text, max_chars=2000, overlap=200) -> list[str]

3) app/api/upload.py
- Router prefix /upload-pdf (POST)
- Accept multipart file
- Validate max size from env MAX_UPLOAD_MB (default 15)
- Save PDF using file_manager.save_upload()
- Extract text + pages via pdf_service
- Save extracted text as .txt under storage/text using file_manager.write_text(file_id,...)
- Return UploadResponse including text_length from extracted text

4) app/main.py
- Ensure router is included
- Ensure static serving:
  - /files -> app/storage/text + docs (choose a clean strategy)
  - /exports -> app/storage/csv

Add proper exception handlers (HTTPException) and logging.
Return full code for changed files.


✅ Test with Postman:

POST http://127.0.0.1:8000/upload-pdf form-data file: your.pdf

Phase 3 — Convert Text to TXT or DOCX API

PROMPT:

Implement conversion endpoint.

Update/Create:

1) app/api/convert.py
- POST /convert-text
- Input ConvertRequest(file_id, output_format)
- Read extracted text from storage/text/{file_id}.txt via file_manager.read_text
- If output_format=txt: ensure txt exists, return download_url "/files/{file_id}.txt"
- If output_format=doc: generate docx via file_manager.write_docx, return "/files/{file_id}.docx"
- Add clear errors if file missing.

2) app/main.py
- Include convert router
- Ensure static /files serves both txt and docx outputs (choose directory strategy)

Return code.


✅ Test:

POST /convert-text JSON { "file_id":"...", "output_format":"doc" }

Phase 4 — Answer Key Randomizer Service + API

PROMPT:

Implement answer key randomizer with strong anti-pattern rules.

Update/Create:

1) app/services/answer_randomizer.py
- Function generate_answer_key(n:int) -> str
Rules:
- Uses a/b/c/d
- Balanced distribution as much as possible
- Avoid >2 same letters in a row
- Avoid repeating patterns like "abcdabcd"
- Should be random but constrained
- Deterministic option: accept optional seed param for testing

2) app/api/mcq.py (only add answer-key endpoint in this phase)
- POST /generate-answer-key
- Input AnswerKeyRequest(total_questions)
- Return AnswerKeyResponse(answer_key)

Return full code.


✅ Test:

POST /generate-answer-key { "total_questions": 25 }

Phase 5 — MCQ Generator (AI layer abstracted) + Generate MCQs API

PROMPT:

Implement MCQ generation engine.

Constraints:
- Must generate MCQs strictly from extracted text.
- Each MCQ: 1 question, 4 unique options, exactly 1 correct.
- Shuffle options AFTER assigning correct answer.
- Avoid repetition of questions.
- Avoid hallucination by grounding: the correct option must be supported by the text chunk used.

Implementation Plan:
1) Create an abstract AI client interface, but also provide a local fallback generator:
- If no AI key provided, generate simple extractive MCQs based on sentences (rule-based).
- If AI key exists, call AI provider (OpenAI/Gemini compatible), but keep code abstract with a placeholder function.

Files to implement/update:

1) app/services/mcq_service.py
- Functions:
  - generate_mcqs_from_text(text:str, total_questions:int, difficulty:str) -> list[McqItem]
  - internal helpers: pick_candidate_facts, build_question, build_distractors, ensure_unique_options, shuffle_options_preserve_answer
- Save generated MCQs into storage (JSON file optional) but must return response.

2) app/api/mcq.py
- POST /generate-mcq
- Input McqRequest(file_id,total_questions,difficulty)
- Read text from file_id
- Call mcq_service.generate_mcqs_from_text
- Return McqResponse

3) app/models/schemas.py
- If needed, add a lightweight McqStore model for export later (optional)

Return complete updated code.


✅ Test:

POST /generate-mcq with {file_id, total_questions: 10, difficulty:"easy"}

Phase 6 — Export MCQs to CSV API

PROMPT:

Implement export to CSV.

Goal: export MCQs generated from /generate-mcq into CSV.

Approach:
- When /generate-mcq runs, also persist mcqs to a JSON file: storage/csv or storage/text as {file_id}_mcqs.json (choose best).
- /export-csv reads persisted MCQs and builds pandas DataFrame:
  columns: Question, Option A, Option B, Option C, Option D, Correct Answer
- Writes CSV to storage/csv and returns /exports/{file_id}.csv

Update/Create:

1) app/api/export.py
- POST /export-csv
- Input ExportCsvRequest(file_id)
- Returns ExportCsvResponse(csv_url)

2) app/utils/file_manager.py
- Add write_json/read_json helpers if needed.

3) app/main.py
- Include export router
- Ensure /exports static route works.

Return code.


✅ Test:

Generate MCQs first, then POST /export-csv { "file_id":"..." }

Phase 7 — README + Postman Collection + Production polish

PROMPT:

Finalize project.

Deliver:
1) README.md with:
- setup steps
- env vars
- run commands
- Postman testing instructions for all endpoints
- sample request/response JSON

2) Add basic Dockerfile + .dockerignore
3) Add global exception handler and consistent error responses
4) Add CORS config (allow localhost frontends)
5) Add health endpoint GET /health

Return all new files and any changed code.