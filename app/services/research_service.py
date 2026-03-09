import os
import json
import uuid
import pandas as pd
import google.generativeai as genai
from typing import List, Dict, Any, Optional
from app.models.schemas import McqItem
from app.utils.file_manager import write_csv, save_generated_pdf
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

load_dotenv()

# Configure Gemini (assuming API key is in env)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

RESEARCH_SYSTEM_PROMPT = """
You are an ADVANCED WEB SCRAPER and EXAM RESEARCHER AI.
Your task is to compile the BEST study material from the web (simulated) for a specific Subject and Topic.

GOAL:
1. Aggregate all top-ranking content.
2. NO REPEATS.
3. Combine all facts properly.
4. Include PYQ (Previous Year Question) facts.
5. Provide high-yield "One-Liner" content.

OUTPUT FORMAT:
Return a JSON object with two fields:
1. "notes": A long Markdown string containing the study notes (bullet points, one-liners, bold key terms).
2. "mcqs": A list of 50 Multiple Choice Questions based on the notes.

MCQ REQUIREMENTS:
- Count: Exactly 50 questions.
- Difficulty: Exam level (mix of easy, medium, hard).
- Options: 4 options (a, b, c, d).
- Answer Key Pattern: SMART RANDOMIZATION (e.g., c, a, b, d, d, a, c, b...). NOT all 'a' or 'b'.
- Format: List of objects { "question": "...", "options": { "a": "...", "b": "...", "c": "...", "d": "..." }, "correct_answer": "a/b/c/d" }
"""

import re
from app.utils.common import safe_json_parse

def generate_research_content(subject: str, topic: str) -> Dict[str, Any]:
    """
    Generates comprehensive notes and 50 MCQs for a given subject and topic.
    """
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 0.3,
            "response_mime_type": "application/json"
        },
        system_instruction=RESEARCH_SYSTEM_PROMPT
    )

    user_prompt = f"""
    RESEARCH TOPIC:
    Subject: {subject}
    Topic: {topic}

    INSTRUCTIONS:
    1. SCRAPE & SYNTHESIZE: Pretend you have scraped the top 20 educational websites and PYQ databases.
    2. NOTES: Create a comprehensive "One-Liner" study guide. Cover definitions, types, examples, exceptions, and key figures.
    3. MCQS: Generate 50 unique MCQs derived from these notes.
    """

    try:
        response = model.generate_content(user_prompt)
        result = safe_json_parse(response.text)
        return result
    except Exception as e:
        print(f"Error generating research content: {e}")
        # Fallback or re-raise
        raise e

CONTENTMAKER_SYSTEM_PROMPT = """
You are an EXPERT EXAM NOTE MAKER for Indian Government Exams (UPPSC, SSC, PCS, RO/ARO, etc.).
You receive raw study material text from multiple PDFs (Hindi / English / bilingual) for ONE topic.

Your job is to create TOP-NOTCH, EXAM-READY ONE-LINER NOTES that are better than any coaching material.

WORKFLOW (ALWAYS FOLLOW THESE STEPS):
STEP 1 → EXTRACT CONTENT
- Read and understand all given text carefully.
- Merge duplicated facts and fix inconsistent wording.

STEP 2 → CHECK TOPIC COVERAGE
- Think of the standard complete outline for this GS/GK topic.
- Example for a history topic like "Gupta Empire":
  Polity & Administration, Economy, Society, Religion, Art & Architecture,
  Literature, Chronology, Important Rulers, Territories, Battles, Decline.
- For science, geography, polity, etc., similarly think of standard sub-headings.

STEP 3 → FILL MISSING TOPICS (USING YOUR OWN KNOWLEDGE)
- If some important sub-area is NOT present in the PDFs, you MUST still cover it
  using your own internal knowledge.
- Add those missing facts as one-liners as well.
- Do NOT mark them separately; integrate everything into one seamless notes set.

STEP 4 → GENERATE FINAL OUTPUT
- Convert everything into ultra-crisp ONE-LINER facts.
- Each line should be exam-useful and information-dense.
- Remove redundancy and trivial fluff.

LANGUAGE RULES:
- If the source is mostly Hindi, write notes in Hindi.
- If the source is mostly English, write notes in English.
- If the source is mixed, you may use natural Hinglish style, like coaching notes.

PYQ ONE-LINER SECTION (MANDATORY AT END):
- At the END of the notes, add a small section titled:
  \"PYQ Style One-Liners\"
- Add 10–20 one-liners that look like facts derived from
  previous year questions of Indian government exams on this topic.
- These are still one-liners (not full MCQs), but should feel like important PYQ facts.

OUTPUT FORMAT:
- Return a plain text block.
- Use simple lines separated by newlines.
- You may use lightweight headings (e.g. 'Administration:', 'Economy:') when helpful,
  but keep most content as one-liner bullets or sentences.
"""

def generate_notes_from_text(base_text: str, topic: Optional[str] = None) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={
            "temperature": 0.2,
        },
        system_instruction=CONTENTMAKER_SYSTEM_PROMPT
    )

    topic_line = ""
    if topic:
        topic_line = f"MAIN TOPIC: {topic}\n\n"

    prompt = f"""
{topic_line}Source study material from multiple PDFs:

{base_text}

Task:
Follow STEP 1 to STEP 4 from the system instruction and produce final one-liner notes plus PYQ style one-liners at the end.
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error generating notes content: {e}")
        raise e

def save_research_csv(mcqs: List[Dict], filename_prefix: str) -> str:
    """
    Saves MCQs to a CSV file and returns the filename.
    """
    data = []
    for i, mcq in enumerate(mcqs, 1):
        row = {
            "Q.No": i,
            "Question": mcq.get("question", ""),
            "Option A": mcq.get("options", {}).get("a", ""),
            "Option B": mcq.get("options", {}).get("b", ""),
            "Option C": mcq.get("options", {}).get("c", ""),
            "Option D": mcq.get("options", {}).get("d", ""),
            "Correct Answer": mcq.get("correct_answer", "").lower()
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    write_csv(filename_prefix, df)
    return f"{filename_prefix}.csv"

def save_research_pdf(notes: str, subject: str, topic: str, filename_prefix: str) -> str:
    """
    Generates and saves a PDF for the research notes.
    Returns the filename.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Study Notes: {subject} - {topic}", styles['Title']))
    story.append(Spacer(1, 12))

    # Notes content processing
    # Split by newlines to handle basic formatting
    lines = notes.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
        
        # Simple Markdown-like header detection
        if line.startswith('###'):
             story.append(Paragraph(line.lstrip('#').strip(), styles['Heading3']))
        elif line.startswith('##'):
             story.append(Paragraph(line.lstrip('#').strip(), styles['Heading2']))
        elif line.startswith('#'):
             story.append(Paragraph(line.lstrip('#').strip(), styles['Heading1']))
        elif line.startswith('- ') or line.startswith('* '):
             story.append(Paragraph(f"• {line[2:]}", styles['Normal']))
        else:
            story.append(Paragraph(line, styles['Normal']))
            
    doc.build(story)
    buffer.seek(0)
    
    # Save using file_manager
    filename = f"{filename_prefix}.pdf"
    return save_generated_pdf(buffer, filename)
