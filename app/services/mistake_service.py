import os
import json
import re
import google.generativeai as genai
from typing import List, Optional, Generator
from app.models.schemas import McqItem

# --- STATIC SYSTEM PROMPT ---
MISTAKE_SYSTEM_PROMPT = """
You are an EXPERT EXAM TUTOR and SUBJECT MATTER EXPERT.
Your goal is to help a student learn from their mistakes.

You will be provided with a list of "Wrong Questions" (questions the student answered incorrectly).

Your tasks are:
1. **ANALYZE** the mistake to understand the missing knowledge.
2. **CREATE ONE-LINER NOTES**:
   - Write comprehensive, detailed, single-sentence facts.
   - Cover the specific fact missed, PLUS related important details (context, dates, figures).
   - "PYQ Fact" style: High-yield, exam-oriented statements.
3. **GENERATE NEW MCQs**:
   - Create FRESH MCQs to test the same concepts but with different phrasing or related angles.
   - DO NOT just copy the old question.
   - Follow the Allahabad High Court exam pattern (Match formatting, Chronology, etc.).
   - Ensure 4 options, 1 correct answer.

OUTPUT FORMAT (JSON Only):
{
  "notes": [
    "Fact 1: ...",
    "Fact 2: ..."
  ],
  "mcqs": [
    {
      "question": "...",
      "options": {"a": "...", "b": "...", "c": "...", "d": "..."},
      "correct_answer": "a"
    }
  ]
}
"""

def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=MISTAKE_SYSTEM_PROMPT
    )

def chunk_text(text: str, max_chars: int = 6000) -> Generator[str, None, None]:
    """Chunks text to fit context window, trying to split at newlines."""
    text = text.replace('\r\n', '\n')
    current_chunk = []
    current_len = 0
    
    # Split by double newlines to keep questions together often
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if current_len + len(para) > max_chars:
            yield "\n\n".join(current_chunk)
            current_chunk = []
            current_len = 0
        current_chunk.append(para)
        current_len += len(para)
        
    if current_chunk:
        yield "\n\n".join(current_chunk)

from app.utils.common import safe_json_parse

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from io import BytesIO

# ... existing code ...

def generate_mistake_pdf(notes: List[str], mcqs: List[McqItem]) -> BytesIO:
    """Generates a PDF report for mistake analysis."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Normal'],
        spaceAfter=10,
        bulletIndent=10,
        leftIndent=20
    )
    
    story = []
    
    # Title
    story.append(Paragraph("Mistake Analysis & Study Plan", title_style))
    story.append(Spacer(1, 20))
    
    # Section 1: Study Notes
    if notes:
        story.append(Paragraph("Key Study Notes", heading_style))
        story.append(Spacer(1, 10))
        for note in notes:
            story.append(Paragraph(f"• {note}", note_style))
        story.append(Spacer(1, 20))
    
    # Section 2: Practice MCQs
    if mcqs:
        story.append(Paragraph("Practice MCQs", heading_style))
        story.append(Spacer(1, 10))
        
        for i, mcq in enumerate(mcqs, 1):
            # Question
            story.append(Paragraph(f"Q{i}: {mcq.question}", styles['Heading3']))
            
            # Options
            options_text = []
            options_text.append(f"A) {mcq.options.get('a', '')}")
            options_text.append(f"B) {mcq.options.get('b', '')}")
            options_text.append(f"C) {mcq.options.get('c', '')}")
            options_text.append(f"D) {mcq.options.get('d', '')}")
            
            for opt in options_text:
                story.append(Paragraph(opt, normal_style))
            
            # Correct Answer (Hidden/Small or Just shown)
            # Let's show it at the bottom of the question for immediate review
            story.append(Spacer(1, 5))
            story.append(Paragraph(f"<b>Correct Answer: {mcq.correct_answer.upper()}</b>", normal_style))
            
            story.append(Spacer(1, 15))

    doc.build(story)
    buffer.seek(0)
    return buffer

def analyze_mistakes_with_ai(text: str) -> Optional[dict]:
    model = get_gemini_model()
    if not model:
        print("Gemini API Key missing.")
        return None

    chunks = list(chunk_text(text))
    all_notes = []
    all_mcqs = []
    seen_notes = set()
    seen_questions = set()

    print(f"Analyzing Mistakes: {len(text)} chars, {len(chunks)} chunks.")

    for i, chunk in enumerate(chunks):
        prompt = f"""
        Analyze the following wrong questions and generate Study Notes + New MCQs.
        
        INPUT DATA:
        {chunk}
        
        REQUIREMENTS:
        - Extract every key fact from these mistakes.
        - Generate clear, dense ONE-LINER NOTES.
        - Create NEW MCQs to test these facts.
        - JSON Output only.
        """
        
        try:
            response = model.generate_content(prompt)
            data = safe_json_parse(response.text)
            
            if not data:
                continue
                
            # Process Notes
            for note in data.get("notes", []):
                if note not in seen_notes:
                    all_notes.append(note)
                    seen_notes.add(note)
            
            # Process MCQs
            for mcq in data.get("mcqs", []):
                q_norm = mcq.get("question", "").strip().lower()
                if q_norm and q_norm not in seen_questions:
                    all_mcqs.append(McqItem(**mcq))
                    seen_questions.add(q_norm)
                    
        except Exception as e:
            print(f"Error processing chunk {i}: {e}")
            continue

    return {
        "notes": all_notes,
        "mcqs": all_mcqs
    }
