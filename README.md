# PDF to MCQ Generator API

A production-ready FastAPI backend that converts PDF documents into high-quality Multiple Choice Questions (MCQs) suitable for government and competitive exams. Features include PDF text extraction, AI-powered generation (Gemini), CSV export, and persistent storage.

## Features

- **PDF Upload**: Extracts text from PDF documents securely.
- **AI-Powered Generation**: Uses Google Gemini Pro to generate high-quality, exam-level MCQs.
- **Rule-Based Fallback**: Robust fallback generator if AI service is unavailable.
- **CSV Export**: Export generated MCQs to CSV for easy use.
- **Persistent Storage**: Saves uploads and generated data locally.

## Setup

1.  **Clone the repository**
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    STORAGE_ROOT=app/storage
    MAX_UPLOAD_MB=15
    LOG_LEVEL=INFO
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

## Running the Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

## API Usage (Postman/Curl)

### 1. Upload PDF
**POST** `/upload-pdf`
- **Body**: `form-data`
- **Key**: `file` (Select PDF file)
- **Response**: `{ "file_id": "uuid..." }`

### 2. Generate MCQs
**POST** `/generate-mcq`
- **Body** (JSON):
  ```json
  {
    "file_id": "uuid...",
    "count": 10,
    "difficulty": "hard"
  }
  ```

### 3. Export CSV
**GET** `/export-csv/{file_id}`

## Directory Structure
- `app/api`: API Routes
- `app/services`: Business logic (PDF, Text, MCQ)
- `app/models`: Pydantic schemas
- `app/utils`: File handling
- `app/storage`: Generated files (Git ignored)
