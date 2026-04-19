from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import ExamGenerationResponse, ExamGenerationRequest, CustomExamRequest, CustomExamResponse
from app.services import mcq_service, dedup_service
import pandas as pd
import uuid
import os
import re
from typing import Dict, List
from app.utils.file_manager import write_csv
from app.utils import file_manager
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

router = APIRouter()

# APS Mock Test weightage (Total = 100)
SYLLABUS = {
    "Indian National Movement": 8,
    "Ancient History": 3,
    "Medieval History": 2,
    "Indian Geography": 5,
    "World Geography": 5,
    "General English": 10,
    "General Hindi": 5,
    "Elementary Knowledge of Computers": 10,
    "Indian Polity": 6,
    "General Science": 7,
    "Uttar Pradesh Special GK": 7,
    "Current Affairs 2025": 10,
    "Reasoning": 10,
    "Economics": 3,
    "Environment & Ecology": 4,
    "Agriculture": 3,
    "Art & Culture": 2,
}

TOTAL_QUESTIONS = sum(SYLLABUS.values())

DIFFICULTY_MAP = {
    "Indian National Movement": {"easy": 2, "medium": 4, "hard": 2},
    "Ancient History": {"easy": 1, "medium": 1, "hard": 1},
    "Medieval History": {"easy": 0, "medium": 1, "hard": 1},
    "Indian Geography": {"easy": 1, "medium": 3, "hard": 1},
    "World Geography": {"easy": 1, "medium": 3, "hard": 1},
    "General English": {"easy": 3, "medium": 5, "hard": 2},
    "General Hindi": {"easy": 2, "medium": 2, "hard": 1},
    "Elementary Knowledge of Computers": {"easy": 3, "medium": 5, "hard": 2},
    "Indian Polity": {"easy": 1, "medium": 4, "hard": 1},
    "General Science": {"easy": 2, "medium": 3, "hard": 2},
    "Uttar Pradesh Special GK": {"easy": 2, "medium": 3, "hard": 2},
    "Current Affairs 2025": {"easy": 3, "medium": 5, "hard": 2},
    "Reasoning": {"easy": 3, "medium": 5, "hard": 2},
    "Economics": {"easy": 1, "medium": 1, "hard": 1},
    "Environment & Ecology": {"easy": 1, "medium": 2, "hard": 1},
    "Agriculture": {"easy": 1, "medium": 1, "hard": 1},
    "Art & Culture": {"easy": 1, "medium": 1, "hard": 0},
}


def _get_subject_difficulty_split(subject: str, total: int) -> Dict[str, int]:
    dmap = DIFFICULTY_MAP.get(subject)
    if isinstance(dmap, dict):
        easy = int(dmap.get("easy", 0))
        medium = int(dmap.get("medium", 0))
        hard = int(dmap.get("hard", 0))
        if easy + medium + hard == total and min(easy, medium, hard) >= 0:
            return {"easy": easy, "medium": medium, "hard": hard}

    base = total // 3
    rem = total - (base * 3)
    split = {"easy": base, "medium": base, "hard": base}
    if rem >= 1:
        split["medium"] += 1
    if rem >= 2:
        split["easy"] += 1
    return split

def get_subtopics_map() -> Dict[str, List[str]]:
    """Parses high-court.md to extract sub-topics for each syllabus subject."""
    file_path = os.path.join(os.path.dirname(__file__), "..", "high-court.md")
    if not os.path.exists(file_path):
        print(f"Warning: Topic file not found at {file_path}")
        return {}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading topic file: {e}")
        return {}
        
    current_section = None
    topics_by_section: Dict[str, List[str]] = {}
    
    # Markers to identify sections in the text file
    section_markers = {
        "Ancient history": "history_ancient",
        "Medieval history": "history_medieval",
        "modern history": "history_modern",
        "Indian Polity": "polity",
        "World Geography": "geography_world",
        "Geography of India": "geography_india",
        "economy": "economy",
        "Physics": "science_physics",
        "chemistry": "science_chemistry",
        "biology": "science_biology",
        "Computer": "computer",
        "Ecosystem": "ecology",
        "Traditional General Knowledge": "gk_static",
        "Uttar Pradesh": "up_special",
        "Mathematic": "math",
        "Reasoning": "reasoning",
        "Hindi Alphabet": "hindi",
        "English": "english", # Matches "English Spotting Error" or "General English"
        "Current Affairs": "current_affairs"
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 1. Check for Section Headers
        found_marker = False
        for marker, key in section_markers.items():
            # precise check to avoid false positives inside sentences
            if marker.lower() in line.lower():
                # specific check for English to avoid matching inside other words if needed
                if marker == "English" and "General English" not in line and "English Spotting" not in line and "English" not in line: 
                     continue
                
                current_section = key
                if current_section not in topics_by_section:
                    topics_by_section[current_section] = []
                found_marker = True
                break
        
        if found_marker:
            continue
            
        # 2. Extract Sub-topic
        if current_section:
            # Cleanup: "1→Subject..." or "1- Stone Age(10)"
            # Remove leading numbers and arrows
            clean = re.sub(r'^[\d\-\.→\s]+', '', line)
            # Remove trailing counts "(10)"
            clean = re.sub(r'\s*\(\d+\)\s*$', '', clean)
            
            if len(clean) > 3 and not clean.lower().startswith("subject topic"):
                topics_by_section[current_section].append(clean)

    # 3. Map to SYLLABUS Keys
    final_map = {
        "Indian National Movement": topics_by_section.get("history_modern", []),
        "Ancient History": topics_by_section.get("history_ancient", []),
        "Medieval History": topics_by_section.get("history_medieval", []),
        "Indian Geography": topics_by_section.get("geography_india", []),
        "World Geography": topics_by_section.get("geography_world", []),
        "General English": topics_by_section.get("english", []),
        "General Hindi": topics_by_section.get("hindi", []),
        "Elementary Knowledge of Computers": topics_by_section.get("computer", []),
        "Indian Polity": topics_by_section.get("polity", []),
        "General Science": topics_by_section.get("science_physics", []) + topics_by_section.get("science_chemistry", []) + topics_by_section.get("science_biology", []),
        "Uttar Pradesh Special GK": topics_by_section.get("up_special", []),
        "Current Affairs 2025": topics_by_section.get("current_affairs", ["Current Affairs 2025 (National)", "Current Affairs 2025 (International)"]),
        "Reasoning": topics_by_section.get("reasoning", []),
        "Economics": topics_by_section.get("economy", []),
        "Environment & Ecology": topics_by_section.get("ecology", []) + ["Biodiversity", "Climate Change", "Conservation", "Pollution", "Ecosystem"],
        "Agriculture": ["Agriculture in India", "Crops and Seasons", "Soils", "Irrigation", "Animal Husbandry"],
        "Art & Culture": topics_by_section.get("gk_static", []),
    }
    
    # Extract Agriculture topics from Geography/Economy if available to populate the Agriculture list
    agri_keywords = ["agriculture", "crop", "soil", "husbandry", "irrigation"]
    extracted_agri = []
    
    for source_list in [topics_by_section.get("geography_india", []), topics_by_section.get("economy", [])]:
        for topic in source_list:
            if any(k in topic.lower() for k in agri_keywords):
                extracted_agri.append(topic)
                
    if extracted_agri:
        final_map["Agriculture"].extend(extracted_agri)

    return final_map

import random


def get_hindi_font_name() -> str | None:
    font_name = "HindiFont"

    # 1. Env-var override
    env_font_path = os.getenv("HINDI_TTF_PATH") or os.getenv("HINDI_FONT_PATH")
    if env_font_path and os.path.exists(env_font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, env_font_path))
            return font_name
        except Exception:
            pass

    # 2. Bundled font (works on all platforms including Railway/Linux)
    bundled = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", "NotoSansDevanagari-Regular.ttf")

    candidates = [
        bundled,
        # Windows
        r"C:\Windows\Fonts\mangal.ttf",
        r"C:\Windows\Fonts\MANGAL.TTF",
        r"C:\Windows\Fonts\nirmala.ttf",
        r"C:\Windows\Fonts\NirmalaUI.ttf",
        r"C:\Windows\Fonts\arialuni.ttf",
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                print(f"  ✅ Hindi font loaded: {path}")
                return font_name
            except Exception:
                continue

    return None


def build_mcq_pdf_buffer(title: str, mcqs: List[Dict[str, str]], font_name: str | None = None) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    if font_name:
        title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontName=font_name)
        heading_style = ParagraphStyle("Heading3Custom", parent=styles["Heading3"], fontName=font_name)
        normal_style = ParagraphStyle("NormalCustom", parent=styles["Normal"], fontName=font_name)
    else:
        title_style = styles["Title"]
        heading_style = styles["Heading3"]
        normal_style = styles["Normal"]

    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 14))

    for i, item in enumerate(mcqs, 1):
        q = item.get("question", "")
        a = item.get("a", "")
        b = item.get("b", "")
        c = item.get("c", "")
        d = item.get("d", "")

        story.append(Paragraph(f"Q{i}. {q}", heading_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"A) {a}", normal_style))
        story.append(Paragraph(f"B) {b}", normal_style))
        story.append(Paragraph(f"C) {c}", normal_style))
        story.append(Paragraph(f"D) {d}", normal_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    buffer.seek(0)
    return buffer

@router.post("/exam/generate-full-test", response_model=ExamGenerationResponse)
async def generate_full_test(request: ExamGenerationRequest):
    all_mcqs = []
    breakdown = {}
    
    print(f"Starting full exam generation ({TOTAL_QUESTIONS} Questions) - Mode: {request.difficulty.upper()}...")
    
    # Load sub-topics from file
    sub_topics_map = get_subtopics_map()
    
    # 1. Generate for each subject
    for subject, count in SYLLABUS.items():
        try:
            print(f"Generating {count} questions for {subject}...")
            
            # Get specific sub-topics for this subject if available
            specific_topics = sub_topics_map.get(subject, [])

            diff_split = _get_subject_difficulty_split(subject, count)
            generated_for_subject = 0

            for diff_label, diff_count in diff_split.items():
                if diff_count <= 0:
                    continue

                mode = "moderate"
                if diff_label == "easy":
                    mode = "easy"
                elif diff_label == "hard":
                    mode = "easy-to-moderate"

                extra_instructions = (
                    "IMPORTANT: Questions must be PYQ-style for Indian competitive exams (APS/RO-ARO/SSC/UPSSC). "
                    "Avoid overly academic framing; keep exam-oriented options and traps."
                )
                if subject.lower() == "reasoning":
                    extra_instructions = (
                        extra_instructions
                        + " IMPORTANT (Reasoning): Generate ONLY logical reasoning questions at HIGH DIFFICULTY level. "
                        "Use complex patterns (multi-step series, 3-4 statement syllogisms, complex coding-decoding, "
                        "5-7 movement direction questions, 4-5 generation blood relations). "
                        "Do NOT generate quantitative aptitude or mathematics questions. "
                        "Make questions time-consuming requiring deep analysis."
                    )

                mcqs = mcq_service.generate_mcqs_from_topic(
                    subject,
                    diff_count,
                    mode,
                    sub_topics=specific_topics,
                    extra_instructions=extra_instructions,
                )

                for item in mcqs:
                    item_dict = item.model_dump()
                    item_dict["Subject"] = subject
                    item_dict["Difficulty"] = diff_label
                    all_mcqs.append(item_dict)
                    generated_for_subject += 1

            breakdown[subject] = generated_for_subject
            
        except Exception as e:
            print(f"Failed to generate for {subject}: {e}")
            breakdown[subject] = 0

    if not all_mcqs:
        raise HTTPException(status_code=500, detail="Failed to generate any questions")

    # 2. Format for DataFrame
    def format_to_row(m_dict, subject):
        return {
            "Question": m_dict['question'],
            "Option A": m_dict['options']['a'],
            "Option B": m_dict['options']['b'],
            "Option C": m_dict['options']['c'],
            "Option D": m_dict['options']['d'],
            "Correct Answer": m_dict['correct_answer'],
            "Difficulty": m_dict.get("Difficulty", ""),
            "Subject": subject,
            "Points": 1
        }

    rows = [format_to_row(m, m.get('Subject', 'General')) for m in all_mcqs]
    df_formatted = pd.DataFrame(rows)

    # 3. Deduplicate using the Hybrid Service
    filename_prefix = f"exam_gen_{request.difficulty}_{uuid.uuid4().hex[:8]}"
    
    print("Running initial deduplication...")
    # Don't save yet, we might need to top up
    dedup_result = dedup_service.remove_semantic_duplicates(df_formatted, filename_prefix, save_output=False)
    current_df = dedup_result['df']
    
    # 4. Top-up Loop to ensure exactly TOTAL_QUESTIONS unique questions
    max_retries = 10
    retry_count = 0
    
    while len(current_df) < TOTAL_QUESTIONS and retry_count < max_retries:
        needed = TOTAL_QUESTIONS - len(current_df)
        print(f"Unique count {len(current_df)} < {TOTAL_QUESTIONS}. Generating {needed} more (Attempt {retry_count+1}/{max_retries})...")
        
        # Pick a random subject to top up (preferring larger subjects slightly, or just random)
        subject = random.choice(list(SYLLABUS.keys()))
        print(f"Top-up Subject: {subject}")
        
        specific_topics = sub_topics_map.get(subject, [])
        # Generate slightly more than needed to ensure uniqueness
        batch_size = max(2, needed + 2) 
        
        try:
            batch_split = _get_subject_difficulty_split(subject, batch_size)
            new_rows = []
            for diff_label, diff_count in batch_split.items():
                if diff_count <= 0:
                    continue

                mode = "moderate"
                if diff_label == "easy":
                    mode = "easy"
                elif diff_label == "hard":
                    mode = "easy-to-moderate"

                extra_instructions = (
                    "IMPORTANT: Questions must be PYQ-style for Indian competitive exams (APS/RO-ARO/SSC/UPSSC). "
                    "Avoid overly academic framing; keep exam-oriented options and traps."
                )
                if subject.lower() == "reasoning":
                    extra_instructions = (
                        extra_instructions
                        + " IMPORTANT (Reasoning): Generate ONLY logical reasoning questions at HIGH DIFFICULTY level. "
                        "Use complex patterns (multi-step series, 3-4 statement syllogisms, complex coding-decoding, "
                        "5-7 movement direction questions, 4-5 generation blood relations). "
                        "Do NOT generate quantitative aptitude or mathematics questions. "
                        "Make questions time-consuming requiring deep analysis."
                    )

                new_mcqs = mcq_service.generate_mcqs_from_topic(
                    subject,
                    diff_count,
                    mode,
                    sub_topics=specific_topics,
                    extra_instructions=extra_instructions,
                )

                for item in new_mcqs:
                    item_dict = item.model_dump()
                    item_dict["Difficulty"] = diff_label
                    new_rows.append(format_to_row(item_dict, subject))
            
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                current_df = pd.concat([current_df, new_df], ignore_index=True)
                
                # Deduplicate again
                dedup_result = dedup_service.remove_semantic_duplicates(current_df, filename_prefix, save_output=False)
                current_df = dedup_result['df']
                
        except Exception as e:
            print(f"Error during top-up generation: {e}")
            
        retry_count += 1

    # 5. Finalize
    final_count = len(current_df)
    if final_count > TOTAL_QUESTIONS:
        print(f"Trimming from {final_count} to {TOTAL_QUESTIONS} questions.")
        current_df = current_df.iloc[:TOTAL_QUESTIONS]
        final_count = TOTAL_QUESTIONS
        
    # Save Final CSV
    final_filename_base = f"{filename_prefix}_cleaned"
    write_csv(final_filename_base, current_df)
    final_csv_url = f"/exports/{final_filename_base}.csv"
    
    return ExamGenerationResponse(
        total_generated=len(all_mcqs) + (len(current_df) - dedup_result['cleaned_count']), # Approx total
        final_unique_count=final_count,
        csv_url=final_csv_url,
        breakdown=breakdown
    )

@router.post("/exam/generate-custom", response_model=CustomExamResponse)
async def generate_custom_test(http_request: Request, request: CustomExamRequest):
    print(f"Starting custom generation for {request.subject} - {request.total_questions} Qs - Mode: {request.difficulty.upper()}...")
    
    try:
        # Generate MCQs
        mcqs = mcq_service.generate_mcqs_from_topic(
            request.subject, 
            request.total_questions, 
            request.difficulty, 
            sub_topics=request.topics
        )
        
        if not mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate questions")

        # Format for DataFrame
        def format_to_row(m):
            item_dict = m.model_dump()
            return {
                "Question": item_dict['question'],
                "Option A": item_dict['options']['a'],
                "Option B": item_dict['options']['b'],
                "Option C": item_dict['options']['c'],
                "Option D": item_dict['options']['d'],
                "Correct Answer": item_dict['correct_answer'],
                "Subject": request.subject,
                "Topics": ", ".join(request.topics),
                "Points": 1
            }

        rows = [format_to_row(m) for m in mcqs]
        df_formatted = pd.DataFrame(rows)
        
        # Deduplicate
        filename_prefix = f"custom_gen_{uuid.uuid4().hex[:8]}"
        print("Running deduplication...")
        
        # Initial deduplication
        dedup_result = dedup_service.remove_semantic_duplicates(df_formatted, filename_prefix, save_output=False)
        current_df = dedup_result['df']
        
        # Top-up Loop
        max_retries = 5
        retry_count = 0
        
        while len(current_df) < request.total_questions and retry_count < max_retries:
            needed = request.total_questions - len(current_df)
            print(f"Top-up: {len(current_df)} < {request.total_questions}. Generating {needed} more...")
            
            new_mcqs = mcq_service.generate_mcqs_from_topic(
                request.subject, 
                max(2, needed + 2), 
                request.difficulty, 
                sub_topics=request.topics
            )
            
            if new_mcqs:
                new_rows = [format_to_row(m) for m in new_mcqs]
                new_df = pd.DataFrame(new_rows)
                current_df = pd.concat([current_df, new_df], ignore_index=True)
                
                # Dedup again
                dedup_result = dedup_service.remove_semantic_duplicates(current_df, filename_prefix, save_output=False)
                current_df = dedup_result['df']
            
            retry_count += 1
            
        # Trim if needed
        if len(current_df) > request.total_questions:
             current_df = current_df.iloc[:request.total_questions]
             
        # Final Save
        final_filename_base = f"{filename_prefix}_cleaned"
        write_csv(final_filename_base, current_df)
        final_csv_url = f"/exports/{final_filename_base}.csv"

        en_items: List[Dict[str, str]] = []
        translate_payload: List[Dict[str, object]] = []
        for _, r in current_df.iterrows():
            question = str(r.get("Question", ""))
            a = str(r.get("Option A", ""))
            b = str(r.get("Option B", ""))
            c = str(r.get("Option C", ""))
            d = str(r.get("Option D", ""))
            correct = str(r.get("Correct Answer", "")).lower()

            en_items.append({"question": question, "a": a, "b": b, "c": c, "d": d})
            translate_payload.append(
                {"question": question, "options": {"a": a, "b": b, "c": c, "d": d}, "correct_answer": correct}
            )

        en_pdf_buffer = build_mcq_pdf_buffer(
            f"Custom Test (English) - {request.subject} - {', '.join(request.topics)}",
            en_items,
        )
        en_pdf_filename = f"{final_filename_base}_en.pdf"
        en_saved = file_manager.save_generated_pdf(en_pdf_buffer, en_pdf_filename)
        en_pdf_url = f"/files/docs/{en_saved}"

        translated = mcq_service.translate_mcqs_to_hindi(translate_payload)
        hi_items: List[Dict[str, str]] = []
        for t in translated:
            opts = t.get("options") or {}
            hi_items.append(
                {
                    "question": str(t.get("question", "")),
                    "a": str(opts.get("a", "")),
                    "b": str(opts.get("b", "")),
                    "c": str(opts.get("c", "")),
                    "d": str(opts.get("d", "")),
                }
            )

        hindi_font = get_hindi_font_name()
        if not hindi_font:
            raise HTTPException(
                status_code=500,
                detail="Hindi PDF font not found. Set HINDI_TTF_PATH to a Devanagari .ttf (e.g., C:\\Windows\\Fonts\\mangal.ttf).",
            )
        hi_pdf_buffer = build_mcq_pdf_buffer(
            f"Custom Test (Hindi) - {request.subject} - {', '.join(request.topics)}",
            hi_items,
            font_name=hindi_font,
        )
        hi_pdf_filename = f"{final_filename_base}_hi.pdf"
        hi_saved = file_manager.save_generated_pdf(hi_pdf_buffer, hi_pdf_filename)
        hi_pdf_url = f"/files/docs/{hi_saved}"

        return CustomExamResponse(
            total_generated=len(current_df),
            final_unique_count=len(current_df),
            csv_url=final_csv_url,
            subject=request.subject,
            pdf_url_en=en_pdf_url,
            pdf_url_hi=hi_pdf_url,
        )

    except Exception as e:
        print(f"Error in custom generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exam/validate-questions")
async def validate_questions(request: Request):
    """
    Validates MCQ questions using AI to check:
    - Question quality and correctness
    - Option validity
    - Correct answer accuracy
    - Duplicate detection
    """
    try:
        from app.services import validation_service
        
        body = await request.json()
        questions = body.get("questions", [])
        
        if not questions:
            raise HTTPException(status_code=400, detail="No questions provided")
        
        print(f"Validating {len(questions)} questions with AI...")
        validation_results = validation_service.validate_mcqs_with_ai(questions)
        
        return validation_results
        
    except Exception as e:
        print(f"Error in validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
