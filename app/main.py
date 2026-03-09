import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.utils import file_manager
from app.api import upload, convert, mcq, export, mistake, research, clean, scraper, exam, rapid

app = FastAPI(title="PDF to MCQ Backend")

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173", # Vite default
    "http://127.0.0.1:5173",
    "*", # Allow all for development convenience
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload.router)
app.include_router(convert.router)
app.include_router(mcq.router)
app.include_router(export.router)
app.include_router(mistake.router)
app.include_router(research.router)
app.include_router(clean.router)
app.include_router(scraper.router)
app.include_router(exam.router)
app.include_router(rapid.router)



# Mount static directories for downloads
# Ensure the directories exist or are handled by file_manager on startup
# We map /files to the storage root for simplicity in this phase, 
# or specific subdirs as requested.
# The prompt asked for /files -> app/storage/text + docs (choose a clean strategy)
# and /exports -> app/storage/csv
# Since StaticFiles serves a single directory, we might need multiple mounts or a parent mount.
# For now, let's mount the storage root to /storage (optional) 
# and specific routes as requested.

STORAGE_ROOT = os.getenv("STORAGE_ROOT", "app/storage")

# We will mount specific subdirectories to match the requirement:
# /files -> serves from text/ and docs/ ? 
# StaticFiles points to one dir. If we want one URL prefix to serve from two dirs, 
# we'd need a custom endpoint or just mount them separately.
# Requirement: /files -> app/storage/text + docs.
# Let's interpret this as: /files/text/... and /files/docs/... OR
# maybe we just mount the parent directory?
# "Serve static downloads from /files and /exports"
# Let's mount 'app/storage' to '/files' for now to cover everything, 
# or be more specific if needed. 
# However, to be "clean", let's mount:
# /files/text -> app/storage/text
# /files/docs -> app/storage/docs
# /exports -> app/storage/csv

app.mount("/files/text", StaticFiles(directory=os.path.join(STORAGE_ROOT, "text"), check_dir=False), name="text_files")
app.mount("/files/docs", StaticFiles(directory=os.path.join(STORAGE_ROOT, "docs"), check_dir=False), name="doc_files")
app.mount("/exports", StaticFiles(directory=os.path.join(STORAGE_ROOT, "csv"), check_dir=False), name="exports")

@app.get("/")
def read_root():
    return {"message": "PDF to MCQ Backend API is running"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
