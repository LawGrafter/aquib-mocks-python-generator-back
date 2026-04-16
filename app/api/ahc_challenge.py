from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import uuid
import os
import random
from app.services import mcq_service
from app.utils.file_manager import write_csv

router = APIRouter()

# AHC Challenge 2026 Syllabus - Exact breakdown
AHC_SYLLABUS = {
    "English": {
        "count": 10,
        "breakdown": [
            {"type": "Synonym", "count": 2},
            {"type": "Antonym", "count": 2},
            {"type": "Spot Error", "count": 2},
            {"type": "Direct & Indirect Speech (long, 2-line sentence)", "count": 1},
            {"type": "Spelling Correction (use difficult word)", "count": 1},
            {"type": "Punctuation Error in sentence", "count": 1},
            {"type": "Active-Passive Voice", "count": 1}
        ]
    },
    "Hindi": {
        "count": 7,
        "breakdown": [
            {"type": "Vilom", "count": 1},
            {"type": "Paryayvachi", "count": 1},
            {"type": "Upsarg", "count": 1},
            {"type": "Pratyay", "count": 1},
            {"type": "Sandhi Viched", "count": 1},
            {"type": "Alankar", "count": 1},
            {"type": "Samas", "count": 1}
        ]
    },
    "Reasoning": {
        "count": 12,
        "breakdown": [
            {"type": "Number/Letter Series", "count": 2},
            {"type": "Syllogism", "count": 2},
            {"type": "Alphabet Series", "count": 1},
            {"type": "Odd One Out", "count": 1},
            {"type": "Coding-Decoding", "count": 2},
            {"type": "Dice", "count": 1},
            {"type": "Calendar (date-based)", "count": 1},
            {"type": "Direction", "count": 1},
            {"type": "Blood Relation", "count": 1}
        ]
    },
    "Computer": {
        "count": 10,
        "breakdown": [
            {"type": "Full Form", "count": 1},
            {"type": "Networking", "count": 1},
            {"type": "Internet Facts", "count": 1},
            {"type": "Printer", "count": 1},
            {"type": "Computer Generation/Invention", "count": 1},
            {"type": "Topology", "count": 1},
            {"type": "Operating System", "count": 1},
            {"type": "MS Word Shortcut Key", "count": 1},
            {"type": "MS PowerPoint Shortcut Key", "count": 1},
            {"type": "MS Excel Shortcut Key", "count": 1}
        ]
    },
    "Economics": {
        "count": 3,
        "breakdown": [
            {"type": "Book & Author", "count": 1},
            {"type": "Fiscal Policy (concept-based)", "count": 1},
            {"type": "Repo Rate & Reverse Repo Rate (statement-based)", "count": 1}
        ]
    },
    "Environment": {
        "count": 3,
        "breakdown": [
            {"type": "Wildlife Sanctuary", "count": 1},
            {"type": "Bird Sanctuary", "count": 1},
            {"type": "Ecological Pyramid", "count": 1}
        ]
    },
    "Polity": {
        "count": 5,
        "breakdown": [
            {"type": "Articles of Constitution", "count": 2},
            {"type": "Making of Indian Constitution (fact-based)", "count": 1},
            {"type": "Chief Minister (article-based)", "count": 1},
            {"type": "Statement-based question from Constituent Assembly members", "count": 1}
        ]
    },
    "Indian National Movement": {
        "count": 9,
        "breakdown": [
            {"type": "Revolt of 1857", "count": 1},
            {"type": "Book & Author", "count": 1},
            {"type": "Newspaper Founder", "count": 1},
            {"type": "Movement-based question", "count": 1},
            {"type": "Charter Acts", "count": 2},
            {"type": "Governor-General/Lord Chronology (year-wise)", "count": 2},
            {"type": "Civil Disobedience Movement (statement-based)", "count": 1}
        ]
    },
    "Ancient History": {
        "count": 3,
        "breakdown": [
            {"type": "Book & Author", "count": 1},
            {"type": "Indus Valley / Rigveda Mandal", "count": 1},
            {"type": "Jainism", "count": 1}
        ]
    },
    "Medieval History": {
        "count": 2,
        "breakdown": [
            {"type": "Book & Author", "count": 1},
            {"type": "Mughal Empire", "count": 1}
        ]
    },
    "Chemistry": {
        "count": 2,
        "breakdown": [
            {"type": "Formula-based", "count": 1},
            {"type": "Metal/Alloy or Everyday Chemistry Fact", "count": 1}
        ]
    },
    "Biology": {
        "count": 3,
        "breakdown": [
            {"type": "Disease-based", "count": 1},
            {"type": "Measuring Instrument", "count": 1},
            {"type": "Animal/Plant Kingdom", "count": 1}
        ]
    },
    "Physics": {
        "count": 3,
        "breakdown": [
            {"type": "Measuring Instrument", "count": 1},
            {"type": "Law-based", "count": 1},
            {"type": "Kinetic/Potential Energy (statement-based)", "count": 1}
        ]
    },
    "World Geography": {
        "count": 5,
        "breakdown": [
            {"type": "Ocean Current", "count": 1},
            {"type": "Mountain", "count": 1},
            {"type": "Grassland", "count": 1},
            {"type": "General World Geography", "count": 2}
        ]
    },
    "Indian Geography": {
        "count": 5,
        "breakdown": [
            {"type": "Peninsular River (statement-based)", "count": 1},
            {"type": "Strait/Channel (Andaman & Nicobar)", "count": 1},
            {"type": "Lesser Himalaya vs Trans Himalaya (statement-based)", "count": 1},
            {"type": "India Boundaries with Neighbor Countries (statement-based)", "count": 1},
            {"type": "Northernmost Point (Indira Col)", "count": 1}
        ]
    },
    "Agriculture": {
        "count": 3,
        "breakdown": [
            {"type": "Soil (Laterite/Red Soil – statement-based)", "count": 1},
            {"type": "Green Revolution (detailed fact-based)", "count": 1},
            {"type": "Irrigation Methods", "count": 1}
        ]
    },
    "Census": {
        "count": 3,
        "breakdown": [
            {"type": "Static/Fact-based questions on Indian Census", "count": 3}
        ]
    },
    "Current Affairs 2025": {
        "count": 4,
        "breakdown": [
            {"type": "Military Exercise (country-wise)", "count": 1},
            {"type": "Important Day & Theme", "count": 1},
            {"type": "Central Government Scheme (Yojana)", "count": 1},
            {"type": "Additional 2025 important current affair", "count": 1}
        ]
    },
    "Art & Culture": {
        "count": 3,
        "breakdown": [
            {"type": "Festival", "count": 1},
            {"type": "Dance", "count": 1},
            {"type": "Gharana", "count": 1}
        ]
    }
}

TOTAL_QUESTIONS = 100

class AHCChallengeRequest(BaseModel):
    difficulty: str = "moderate"  # easy, moderate, hard

class AHCChallengeResponse(BaseModel):
    total_generated: int
    final_count: int
    csv_url: str
    breakdown: Dict[str, int]

def generate_ahc_system_prompt(subject: str, question_type: str, difficulty: str) -> str:
    """Generate specialized system prompt for AHC Challenge 2026"""
    
    difficulty_instruction = {
        "easy": "Generate EASY level questions suitable for beginners. Use straightforward facts and common knowledge.",
        "moderate": "Generate MODERATE level questions with balanced difficulty. Mix direct facts with analytical thinking.",
        "hard": "Generate HARD level questions that require deep knowledge and critical thinking. Use tricky options and complex scenarios."
    }
    
    return f"""You are an expert exam setter for Allahabad High Court (AHC) Challenge 2026.

SUBJECT: {subject}
QUESTION TYPE: {question_type}
DIFFICULTY: {difficulty.upper()}

{difficulty_instruction.get(difficulty, difficulty_instruction['moderate'])}

CRITICAL INSTRUCTIONS:
1. Generate ONLY {question_type} type questions for {subject}
2. Questions must be exam-oriented and factual
3. All 4 options (A, B, C, D) must be plausible and distinct
4. Correct answer must be clearly identifiable
5. Use proper grammar and formatting
6. For statement-based questions, create 2-3 line detailed statements
7. For chronology questions, use proper year/date format
8. Avoid ambiguous or controversial questions

RESPONSE FORMAT:
Return ONLY valid JSON array of MCQ objects. Each object must have:
- "question": string (the question text)
- "options": object with keys "a", "b", "c", "d"
- "correct_answer": string (one of: "a", "b", "c", "d")

Example:
[
  {{
    "question": "Who among the following introduced the Subsidiary Alliance system?",
    "options": {{
      "a": "Lord Cornwallis",
      "b": "Lord Dalhousie",
      "c": "Lord Wellesley",
      "d": "Lord Hastings"
    }},
    "correct_answer": "c"
  }}
]

Generate exactly the required number of questions for this type.
"""

def _get_type_instructions(subject: str, question_type: str, difficulty: str) -> str:
    """Generate specific instructions per question type to ensure diverse formats"""
    
    base = f"""IMPORTANT RULES:
- Difficulty: {difficulty.upper()}
- Subject: {subject}
- Question Type: {question_type}
- DO NOT use "Consider the following statements" format.
- DO NOT use "1 and 2 only / 2 and 3 only / 1, 2 and 3" style options.
- Each question MUST be a direct, clear, single-line question.
- Options must be specific names, terms, dates, facts — NOT statement combinations.
- Randomize correct answer position across a, b, c, d.
"""

    type_map = {
        # English
        "Synonym": "Generate: 'Choose the word most similar in meaning to [WORD]'. Options = 4 different words. Use advanced vocabulary.",
        "Antonym": "Generate: 'Choose the word most opposite in meaning to [WORD]'. Options = 4 different words. Use advanced vocabulary.",
        "Spot Error": "Generate: A sentence divided into parts (a), (b), (c), (d). Ask 'Which part has an error?'. Option d can be 'No Error'.",
        "Direct & Indirect Speech (long, 2-line sentence)": "Generate a long 2-line sentence in direct speech. Ask to convert to indirect speech. Options = 4 different indirect versions.",
        "Spelling Correction (use difficult word)": "Generate: 'Which of the following words is correctly spelt?'. Options = 4 words, only 1 correct spelling. Use difficult English words.",
        "Punctuation Error in sentence": "Generate a sentence with punctuation errors. Ask 'Which version is correctly punctuated?'. Options = 4 versions.",
        "Active-Passive Voice": "Generate a sentence in active voice. Ask to convert to passive voice. Options = 4 passive versions.",
        
        # Hindi
        "Vilom": "Generate: '[WORD] का विलोम शब्द क्या है?'. Options = 4 Hindi words. Use standard Hindi vocabulary.",
        "Paryayvachi": "Generate: '[WORD] का पर्यायवाची शब्द क्या है?'. Options = 4 Hindi words.",
        "Upsarg": "Generate: 'निम्नलिखित में से किस शब्द में [X] उपसर्ग है?' OR 'शब्द [X] में कौन सा उपसर्ग है?'. Options = 4 specific prefixes or words.",
        "Pratyay": "Generate: 'शब्द [X] में कौन सा प्रत्यय है?' OR 'निम्नलिखित में से किस शब्द में [X] प्रत्यय लगा है?'. Options = 4 specific suffixes or words.",
        "Sandhi Viched": "Generate: '[COMPOUND_WORD] का संधि विच्छेद क्या है?'. Options = 4 different splits.",
        "Alankar": "Generate: 'इस पंक्ति में कौन सा अलंकार है? [VERSE]'. Options = 4 alankar names (उपमा, रूपक, अनुप्रास, यमक etc.).",
        "Samas": "Generate: '[COMPOUND_WORD] में कौन सा समास है?'. Options = 4 samas types (तत्पुरुष, द्विगु, कर्मधारय, बहुव्रीहि etc.).",
        
        # Reasoning (High difficulty, time-consuming)
        "Number/Letter Series": "Generate: 'What comes next in the series: X, Y, Z, ?' Use COMPLEX patterns like alternating operations, mixed number-letter series, squares/cubes with modifications, or multi-step mathematical operations. Each question must use a DIFFERENT complex pattern.",
        "Syllogism": "Generate: 'All A are B. Some B are C. No C are D. Some D are A. Conclusion: ?' format with 3-4 statements and complex relationships. Options = 4 specific conclusions. Use classical syllogism format with possibility/probability-based conclusions.",
        "Alphabet Series": "Generate: 'What comes next: A, D, G, J, ?' or letter pattern with SKIP patterns, reverse alphabet, position-based operations, or mixed letter-number patterns. Options = 4 letters. Use a UNIQUE complex pattern.",
        "Odd One Out": "Generate: 'Which one is different from the rest?' with SUBTLE differences requiring deep analysis (e.g., word relationships, number properties, pattern recognition). Options = 4 items where 3 share a complex common property.",
        "Coding-Decoding": "Generate: 'If APPLE is coded as XYZAB, then MANGO is coded as?' using COMPLEX coding rules like letter shifting with varying steps, reverse coding, symbol substitution, or multi-step patterns. Options = 4 coded words. Each question must use a different complex coding rule.",
        "Dice": "Generate a dice-based question with 2-3 dice described showing different positions. Ask which face is opposite to a given face based on rotation logic. Options = 4 faces. Use complex rotation scenarios.",
        "Calendar (date-based)": "Generate: 'What day of the week was [specific date]?' or 'If Jan 1, 2025 was Wednesday, what day is March 15, 2028?' with leap years, long date ranges, or repeated pattern calculations. Options = 4 days.",
        "Direction": "Generate: 'A person walks 5km North, turns right, walks 3km, turns 45° left...' with 5-7 movements, varying angles, and ask final direction/distance from starting point. Options = 4 directions/distances.",
        "Blood Relation": "Generate: 'A is father of B. B is sister of C. C is married to D. D is son of E. How is A related to E?' with 4-5 generations and complex family tree. Options = 4 relations.",
        
        # Computer
        "Full Form": "Generate: 'What is the full form of [ACRONYM]?' (e.g., HTTP, RAM, BIOS, URL). Options = 4 full forms.",
        "Networking": "Generate a factual question about networking (protocols, layers, devices). Options = 4 specific terms.",
        "Internet Facts": "Generate a factual question about the internet (inventor, first website, protocols). Options = 4 specific facts.",
        "Printer": "Generate a question about printer types or technology (laser, inkjet, dot matrix). Options = 4 specific answers.",
        "Computer Generation/Invention": "Generate: 'Which generation of computers used [technology]?' or 'Who invented [device]?'. Options = 4 specific answers.",
        "Topology": "Generate a question about network topologies (star, bus, ring, mesh). Options = 4 topology names or descriptions.",
        "Operating System": "Generate a factual question about OS concepts (kernel, process, memory management). Options = 4 specific terms.",
        "MS Word Shortcut Key": "Generate: 'What is the shortcut key for [action] in MS Word?' Options = 4 keyboard shortcuts (Ctrl+X format).",
        "MS PowerPoint Shortcut Key": "Generate: 'What is the shortcut key for [action] in MS PowerPoint?' Options = 4 keyboard shortcuts.",
        "MS Excel Shortcut Key": "Generate: 'What is the shortcut key for [action] in MS Excel?' Options = 4 keyboard shortcuts.",
        
        # History & Others
        "Book & Author": "Generate: 'Who is the author of the book [BOOK NAME]?' Options = 4 author names. Use well-known books relevant to the subject.",
        "Revolt of 1857": "Generate a direct factual question about the Revolt of 1857 (leaders, places, causes). Options = 4 specific facts.",
        "Newspaper Founder": "Generate: 'Who founded the newspaper [NAME]?' or 'Which newspaper was founded by [PERSON]?'. Options = 4 names.",
        "Movement-based question": "Generate a factual question about Indian independence movements. Options = 4 specific facts.",
        "Charter Acts": "Generate a factual question about Charter Acts (1793, 1813, 1833, 1853). Options = 4 specific provisions or years.",
        "Governor-General/Lord Chronology (year-wise)": "Generate: 'Who was the Governor-General during [event/year]?' or 'Arrange in chronological order'. Options = 4 names or sequences.",
        "Civil Disobedience Movement (statement-based)": "Generate a direct factual question about the Civil Disobedience Movement (1930). Ask 'Which of the following is correct about CDM?' Options = 4 specific facts (NOT statement combinations).",
        "Swadeshi Movement (statement-based)": "Generate a direct factual question about the Swadeshi Movement. Options = 4 specific facts.",
        "Indus Valley / Rigveda Mandal": "Generate a factual question about Indus Valley Civilization or Rigveda. Options = 4 specific facts.",
        "Jainism": "Generate a factual question about Jainism (Tirthankaras, principles, councils). Options = 4 specific facts.",
        "Mughal Empire": "Generate a factual question about the Mughal Empire (rulers, battles, architecture). Options = 4 specific facts.",
        
        # Science
        "Formula-based": "Generate: 'What is the chemical formula of [substance]?' Options = 4 chemical formulas.",
        "Metal/Alloy or Everyday Chemistry Fact": "Generate a factual question about metals, alloys, or everyday chemistry. Options = 4 specific answers.",
        "Disease-based": "Generate: 'Which disease is caused by [pathogen/deficiency]?' or 'What causes [disease]?'. Options = 4 specific diseases/causes.",
        "Measuring Instrument": "Generate: 'Which instrument is used to measure [quantity]?' Options = 4 instrument names.",
        "Animal/Plant Kingdom": "Generate a factual question about animal/plant classification or biology facts. Options = 4 specific terms.",
        "Law-based": "Generate: 'Which law/principle states that [description]?' Options = 4 law names (Newton, Boyle, Archimedes etc.).",
        "Kinetic/Potential Energy (statement-based)": "Generate a direct factual question about kinetic or potential energy. Options = 4 specific physics facts (NOT statement combinations).",
        
        # Geography
        "Ocean Current": "Generate: 'Which ocean current flows along [coast/region]?' or '[Current] is a warm/cold current of?'. Options = 4 current names or regions.",
        "Mountain": "Generate a factual question about world mountains (highest peak, location, range). Options = 4 specific facts.",
        "Grassland": "Generate: 'Which grassland is found in [region]?' or '[NAME] grassland belongs to which continent?'. Options = 4 grassland names.",
        "General World Geography": "Generate a direct factual question about world geography. Options = 4 specific facts.",
        "Peninsular River (statement-based)": "Generate a factual question about peninsular rivers of India (Godavari, Krishna, Narmada). Options = 4 specific facts.",
        "Strait/Channel (Andaman & Nicobar)": "Generate a factual question about straits/channels near Andaman & Nicobar. Options = 4 specific geographic facts.",
        "Lesser Himalaya vs Trans Himalaya (statement-based)": "Generate a factual question comparing Lesser Himalaya and Trans Himalaya features. Options = 4 specific facts.",
        "India Boundaries with Neighbor Countries (statement-based)": "Generate: 'Which Indian state shares border with [country]?' or boundary-related fact. Options = 4 states/countries.",
        "Northernmost Point (Indira Col)": "Generate a factual question about extreme points of India (Indira Col, Indira Point etc.). Options = 4 specific places.",
        
        # Others
        "Fiscal Policy (concept-based)": "Generate a direct factual question about fiscal policy concepts. Options = 4 specific economic terms.",
        "Repo Rate & Reverse Repo Rate (statement-based)": "Generate a factual question about RBI rates (repo, reverse repo, CRR, SLR). Options = 4 specific rates or facts.",
        "Wildlife Sanctuary": "Generate: 'Where is [sanctuary] located?' or 'Which wildlife sanctuary is famous for [animal]?'. Options = 4 specific places/sanctuaries.",
        "Bird Sanctuary": "Generate a factual question about bird sanctuaries in India. Options = 4 specific sanctuaries or places.",
        "Ecological Pyramid": "Generate a factual question about ecological pyramids (energy, biomass, numbers). Options = 4 specific terms.",
        "Articles of Constitution": "Generate: 'Article [X] of the Indian Constitution deals with?' or 'Which article provides for [right]?'. Options = 4 specific articles or rights.",
        "Making of Indian Constitution (fact-based)": "Generate a factual question about the making of the Constitution (dates, committees, members). Options = 4 specific facts.",
        "Chief Minister (article-based)": "Generate a question about constitutional provisions for Chief Minister. Options = 4 specific articles or facts.",
        "Statement-based question from Constituent Assembly members": "Generate: 'Who said [quote] in the Constituent Assembly?' or fact about CA members. Options = 4 specific names.",
        "Soil (Laterite/Red Soil – statement-based)": "Generate a factual question about Indian soil types (laterite, red, alluvial, black). Options = 4 specific soil facts.",
        "Green Revolution (detailed fact-based)": "Generate a factual question about the Green Revolution (year, person, crops, states). Options = 4 specific facts.",
        "Irrigation Methods": "Generate a factual question about irrigation methods in India (drip, canal, well). Options = 4 specific methods or facts.",
        "Static/Fact-based questions on Indian Census": "Generate a factual question about Indian Census (2011 data, most/least populated, literacy rate). Options = 4 specific statistics.",
        "Military Exercise (country-wise)": "Generate: 'Exercise [NAME] is conducted between India and which country?'. Options = 4 country names.",
        "Important Day & Theme": "Generate: 'What is the theme of [Day] in 2025?'. Options = 4 specific themes.",
        "Central Government Scheme (Yojana)": "Generate a factual question about a central government scheme launched in 2024-25. Options = 4 specific scheme names or facts.",
        "Additional 2025 important current affair": "Generate a factual current affairs question from 2025 (awards, appointments, events). Options = 4 specific facts.",
        "Festival": "Generate a factual question about Indian festivals (state, significance, month). Options = 4 specific festivals or states.",
        "Dance": "Generate: 'Which classical dance form belongs to [state]?' or '[Dance] is performed in which state?'. Options = 4 dance names or states.",
        "Gharana": "Generate: 'Which Gharana is associated with [art form/artist]?' or '[Gharana] belongs to which music style?'. Options = 4 gharana names.",
    }
    
    specific = type_map.get(question_type, f"Generate a direct factual question about {question_type} in {subject}. Options = 4 specific answers.")
    
    return f"""{base}
SPECIFIC FORMAT: {specific}
"""


def _generate_for_type(subject: str, question_type: str, count: int, difficulty: str, max_attempts: int = 3) -> list:
    """Generate questions for a specific type with retries. Returns list of mcq dicts."""
    extra_instructions = _get_type_instructions(subject, question_type, difficulty)
    results = []
    
    for attempt in range(max_attempts):
        if len(results) >= count:
            break
        remaining = count - len(results)
        try:
            mcqs = mcq_service.generate_mcqs_from_topic(
                topic=f"{subject} - {question_type}",
                count=remaining + 1,  # Ask for 1 extra to account for parsing failures
                difficulty_mode=difficulty,
                sub_topics=[question_type],
                extra_instructions=extra_instructions
            )
            for mcq in mcqs:
                if len(results) >= count:
                    break
                mcq_dict = mcq.model_dump()
                mcq_dict["Subject"] = subject
                mcq_dict["Question_Type"] = question_type
                mcq_dict["Difficulty"] = difficulty
                results.append(mcq_dict)
                
        except Exception as e:
            print(f"      Attempt {attempt+1}/{max_attempts} failed for [{subject} > {question_type}]: {e}")
            continue
    
    return results


@router.post("/ahc-challenge/generate", response_model=AHCChallengeResponse)
async def generate_ahc_challenge(request: AHCChallengeRequest):
    """
    Generate AHC Challenge 2026 exam with exact syllabus breakdown.
    Ensures every subject gets its required number of questions.
    """
    all_mcqs = []
    breakdown = {}
    # Track shortfalls per subject for targeted retry
    shortfall_tracker = {}  # {subject: [(question_type, still_needed), ...]}
    
    print(f"\n{'='*60}")
    print(f"  AHC Challenge 2026 - Difficulty: {request.difficulty.upper()}")
    print(f"  Target: {TOTAL_QUESTIONS} questions across {len(AHC_SYLLABUS)} subjects")
    print(f"{'='*60}")
    
    try:
        # ============================================
        # PASS 1: Generate for each subject & type
        # ============================================
        for subject, details in AHC_SYLLABUS.items():
            expected = details['count']
            print(f"\n📚 [{subject}] Target: {expected} questions")
            subject_mcqs = []
            subject_shortfalls = []
            
            for item in details['breakdown']:
                question_type = item['type']
                count = item['count']
                
                print(f"  ├─ {question_type}: {count} question(s)...", end=" ")
                
                type_mcqs = _generate_for_type(subject, question_type, count, request.difficulty)
                subject_mcqs.extend(type_mcqs)
                
                if len(type_mcqs) >= count:
                    print(f"✅ {len(type_mcqs)}/{count}")
                else:
                    shortfall = count - len(type_mcqs)
                    subject_shortfalls.append((question_type, shortfall))
                    print(f"⚠️ {len(type_mcqs)}/{count} (missing {shortfall})")
            
            all_mcqs.extend(subject_mcqs)
            breakdown[subject] = len(subject_mcqs)
            
            if subject_shortfalls:
                shortfall_tracker[subject] = subject_shortfalls
            
            status = "✅" if len(subject_mcqs) >= expected else "⚠️"
            print(f"  └─ {status} {subject}: {len(subject_mcqs)}/{expected}")
        
        # ============================================
        # PASS 2: Targeted retry for failed subjects
        # ============================================
        if shortfall_tracker:
            print(f"\n{'─'*40}")
            print(f"🔄 PASS 2: Retrying {len(shortfall_tracker)} subjects with shortfalls")
            print(f"{'─'*40}")
            
            for subject, shortfalls in shortfall_tracker.items():
                for question_type, needed in shortfalls:
                    print(f"  🔄 Retrying [{subject} > {question_type}]: need {needed} more...", end=" ")
                    
                    retry_mcqs = _generate_for_type(subject, question_type, needed, request.difficulty, max_attempts=3)
                    
                    if retry_mcqs:
                        all_mcqs.extend(retry_mcqs)
                        breakdown[subject] = breakdown.get(subject, 0) + len(retry_mcqs)
                        print(f"✅ Got {len(retry_mcqs)}")
                    else:
                        print(f"❌ Failed again")
        
        # ============================================
        # PASS 3: Fill any remaining gap from subjects that are still short
        # ============================================
        if len(all_mcqs) < TOTAL_QUESTIONS:
            print(f"\n{'─'*40}")
            print(f"🔄 PASS 3: Top-up needed. Have {len(all_mcqs)}/{TOTAL_QUESTIONS}")
            print(f"{'─'*40}")
            
            # Find subjects that are short of their target
            for top_up_round in range(3):
                if len(all_mcqs) >= TOTAL_QUESTIONS:
                    break
                    
                for subject, details in AHC_SYLLABUS.items():
                    if len(all_mcqs) >= TOTAL_QUESTIONS:
                        break
                    
                    current_count = breakdown.get(subject, 0)
                    target_count = details['count']
                    
                    if current_count < target_count:
                        # This subject is still short — retry its first breakdown type
                        still_needed = min(target_count - current_count, TOTAL_QUESTIONS - len(all_mcqs))
                        qt = details['breakdown'][0]['type']
                        
                        print(f"  🔄 Round {top_up_round+1}: [{subject}] need {still_needed} more...", end=" ")
                        
                        fill_mcqs = _generate_for_type(subject, qt, still_needed, request.difficulty, max_attempts=2)
                        
                        if fill_mcqs:
                            all_mcqs.extend(fill_mcqs)
                            breakdown[subject] = breakdown.get(subject, 0) + len(fill_mcqs)
                            print(f"✅ Got {len(fill_mcqs)}")
                        else:
                            print(f"❌ Failed")
                
                # If still short, try ANY subject that can give us more
                if len(all_mcqs) < TOTAL_QUESTIONS:
                    subjects_list = list(AHC_SYLLABUS.keys())
                    random.shuffle(subjects_list)
                    
                    for subj in subjects_list:
                        if len(all_mcqs) >= TOTAL_QUESTIONS:
                            break
                        still_needed = min(2, TOTAL_QUESTIONS - len(all_mcqs))
                        detail = AHC_SYLLABUS[subj]
                        qt = detail['breakdown'][0]['type']
                        
                        print(f"  🔄 Extra fill: [{subj}] +{still_needed}...", end=" ")
                        
                        fill_mcqs = _generate_for_type(subj, qt, still_needed, request.difficulty, max_attempts=1)
                        if fill_mcqs:
                            all_mcqs.extend(fill_mcqs)
                            breakdown[subj] = breakdown.get(subj, 0) + len(fill_mcqs)
                            print(f"✅ Got {len(fill_mcqs)}")
                        else:
                            print(f"❌")
        
        if not all_mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate any questions")
        
        # Trim to exactly 100 if we got more
        if len(all_mcqs) > TOTAL_QUESTIONS:
            all_mcqs = all_mcqs[:TOTAL_QUESTIONS]
        
        # ============================================
        # FINAL REPORT
        # ============================================
        print(f"\n{'='*60}")
        print(f"  FINAL REPORT")
        print(f"{'='*60}")
        total = 0
        for subject, details in AHC_SYLLABUS.items():
            actual = breakdown.get(subject, 0)
            expected = details['count']
            status = "✅" if actual >= expected else f"⚠️ (short by {expected - actual})"
            print(f"  {subject:30s} {actual:3d}/{expected:3d}  {status}")
            total += actual
        print(f"{'─'*60}")
        print(f"  {'TOTAL':30s} {len(all_mcqs):3d}/{TOTAL_QUESTIONS}")
        print(f"{'='*60}")
        
        # Format for CSV
        def format_to_row(m_dict):
            return {
                "Question": m_dict['question'],
                "Option A": m_dict['options']['a'],
                "Option B": m_dict['options']['b'],
                "Option C": m_dict['options']['c'],
                "Option D": m_dict['options']['d'],
                "Correct Answer": m_dict['correct_answer'],
                "Points": 1
            }
        
        rows = [format_to_row(m) for m in all_mcqs]
        df = pd.DataFrame(rows)
        
        # Save CSV
        filename_base = f"ahc_challenge_2026_{request.difficulty}_{uuid.uuid4().hex[:8]}"
        write_csv(filename_base, df)
        csv_url = f"/exports/{filename_base}.csv"
        
        return AHCChallengeResponse(
            total_generated=len(all_mcqs),
            final_count=len(all_mcqs),
            csv_url=csv_url,
            breakdown=breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in AHC Challenge generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
