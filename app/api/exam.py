from fastapi import APIRouter, HTTPException
from app.models.schemas import ExamGenerationResponse, ExamGenerationRequest, CustomExamRequest, CustomExamResponse
from app.services import mcq_service, dedup_service
import pandas as pd
import uuid
import os
import re
from typing import Dict, List
from app.utils.file_manager import write_csv

router = APIRouter()

# Exact syllabus count = 150
SYLLABUS = {
    "History of India": 10,
    "General Science": 10,
    "Indian National Movement": 10,
    "Indian Agriculture, Commerce & Trade": 10,
    "Current National & International Events": 10,
    "Indian Polity, Economy & Culture": 15,
    "World Geography & Geography of India": 15,
    "Population, Ecology & Urbanisation (India context)": 10,
    "Reasoning & General Aptitude": 15,
    "General English": 10,
    "General Hindi": 10,
    "Uttar Pradesh Special Knowledge": 10,
    "Elementary Knowledge of Computers": 15
}

def get_subtopics_map() -> Dict[str, List[str]]:
    """Parses high-court.md to extract sub-topics for each syllabus subject."""
    file_path = r"c:\Users\dell\Desktop\Mock test\app\high-court.md"
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
        "History of India": topics_by_section.get("history_ancient", []) + topics_by_section.get("history_medieval", []),
        "Indian National Movement": topics_by_section.get("history_modern", []),
        "General Science": topics_by_section.get("science_physics", []) + topics_by_section.get("science_chemistry", []) + topics_by_section.get("science_biology", []),
        "Indian Agriculture, Commerce & Trade": ["Agriculture in India", "Crops and Seasons", "Animal Husbandry", "Trade and Commerce", "Major Industries"], 
        "Current National & International Events": topics_by_section.get("current_affairs", ["Recent National Events", "International Summits", "Sports Awards", "New Appointments"]),
        "Indian Polity, Economy & Culture": topics_by_section.get("polity", []) + topics_by_section.get("economy", []) + topics_by_section.get("gk_static", []),
        "World Geography & Geography of India": topics_by_section.get("geography_world", []) + topics_by_section.get("geography_india", []),
        "Population, Ecology & Urbanisation (India context)": topics_by_section.get("ecology", []) + ["Census 2011", "Urbanisation Trends", "Population Density"],
        "Reasoning & General Aptitude": topics_by_section.get("reasoning", []) + topics_by_section.get("math", []),
        "General English": topics_by_section.get("english", []),
        "General Hindi": topics_by_section.get("hindi", []),
        "Uttar Pradesh Special Knowledge": topics_by_section.get("up_special", []),
        "Elementary Knowledge of Computers": topics_by_section.get("computer", [])
    }
    
    # Extract Agriculture topics from Geography/Economy if available to populate the Agriculture list
    agri_keywords = ["agriculture", "crop", "soil", "husbandry", "irrigation"]
    extracted_agri = []
    
    for source_list in [topics_by_section.get("geography_india", []), topics_by_section.get("economy", [])]:
        for topic in source_list:
            if any(k in topic.lower() for k in agri_keywords):
                extracted_agri.append(topic)
                
    if extracted_agri:
        final_map["Indian Agriculture, Commerce & Trade"].extend(extracted_agri)

    return final_map

import random

@router.post("/exam/generate-full-test", response_model=ExamGenerationResponse)
async def generate_full_test(request: ExamGenerationRequest):
    all_mcqs = []
    breakdown = {}
    
    print(f"Starting full exam generation (150 Questions) - Mode: {request.difficulty.upper()}...")
    
    # Load sub-topics from file
    sub_topics_map = get_subtopics_map()
    
    # 1. Generate for each subject
    for subject, count in SYLLABUS.items():
        try:
            print(f"Generating {count} questions for {subject}...")
            
            # Get specific sub-topics for this subject if available
            specific_topics = sub_topics_map.get(subject, [])
            
            # Pass the difficulty mode and sub-topics to the service
            mcqs = mcq_service.generate_mcqs_from_topic(subject, count, request.difficulty, sub_topics=specific_topics)
            
            # Convert to dict and add Subject
            for item in mcqs:
                # item is McqItem (Pydantic)
                item_dict = item.model_dump()
                item_dict['Subject'] = subject
                all_mcqs.append(item_dict)
                
            breakdown[subject] = len(mcqs)
            
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
    
    # 4. Top-up Loop to ensure exactly 150 unique questions
    max_retries = 10
    retry_count = 0
    
    while len(current_df) < 150 and retry_count < max_retries:
        needed = 150 - len(current_df)
        print(f"Unique count {len(current_df)} < 150. Generating {needed} more (Attempt {retry_count+1}/{max_retries})...")
        
        # Pick a random subject to top up (preferring larger subjects slightly, or just random)
        subject = random.choice(list(SYLLABUS.keys()))
        print(f"Top-up Subject: {subject}")
        
        specific_topics = sub_topics_map.get(subject, [])
        # Generate slightly more than needed to ensure uniqueness
        batch_size = max(2, needed + 2) 
        
        try:
            new_mcqs = mcq_service.generate_mcqs_from_topic(subject, batch_size, request.difficulty, sub_topics=specific_topics)
            
            new_rows = []
            for item in new_mcqs:
                item_dict = item.model_dump()
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
    if final_count > 150:
        print(f"Trimming from {final_count} to 150 questions.")
        current_df = current_df.iloc[:150]
        final_count = 150
        
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
async def generate_custom_test(request: CustomExamRequest):
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

        return CustomExamResponse(
            total_generated=len(current_df),
            final_unique_count=len(current_df),
            csv_url=final_csv_url,
            subject=request.subject
        )

    except Exception as e:
        print(f"Error in custom generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
