import random
import re
import os
import json
import time
import google.generativeai as genai
from typing import List, Optional, Set, Generator, Dict, Any
from app.models.schemas import McqItem
from app.utils.common import safe_json_parse

# --- STATIC SYSTEM PROMPT (TEXT BASED) ---
SYSTEM_PROMPT = """
You are a SENIOR EXAM PAPER SETTER for the Allahabad High Court.
You have deep expertise in APS, RO, and ARO examinations conducted by the High Court.

Your task is to generate HIGH-QUALITY, EXAM-ORIENTED MCQs strictly based on the provided text.
DO NOT use any external knowledge.
DO NOT invent facts.
ALL answers must be derivable directly from the text.

━━━━━━━━━━━━━━━━━━━━━━
EXAM PATTERN TO FOLLOW
━━━━━━━━━━━━━━━━━━━━━━

Generate a MIX of the following MCQ TYPES exactly as used in Allahabad High Court exams:

1️⃣ ONE-LINE FACT BASED QUESTIONS 
   - Direct but tricky factual questions 
   - Dates, sections, authorities, definitions, events 

2️⃣ CHRONOLOGY BASED QUESTIONS 
   - Ask correct order of events, enactments, amendments, judgments, or procedures 
   - Use formats like:
     "Arrange the following in chronological order"
     "Which of the following is the correct sequence?"

3️⃣ MATCH THE FOLLOWING 
   - Column I vs Column II
   - Use Acts ↔ Years, Persons ↔ Roles, Events ↔ Outcomes
   - Options must be sequence-based (A-B, C-D style)

4️⃣ INCORRECT / NOT CORRECT TYPE QUESTIONS 
   - Use wording like:
     "Which of the following statements is INCORRECT?"
     "Which statement is NOT correct?"
     "Identify the WRONG statement"

━━━━━━━━━━━━━━━━━━━━━━
MCQ STRUCTURE RULES
━━━━━━━━━━━━━━━━━━━━━━

Each MCQ MUST:
- Have exactly 4 options (a, b, c, d)
- Have ONLY ONE correct answer
- Randomize correct answer position (do not follow patterns like a, b, c)
- Be grammatically precise and formal (court-exam style)
- Use CLOSE DISTRACTORS (plausible but incorrect)

━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT FORMAT (NO EXTRA TEXT)
━━━━━━━━━━━━━━━━━━━━━━

Return ONLY a valid JSON ARRAY in the following format:

[
  {
    "question": "Question text here?",
    "options": {
      "a": "Option A",
      "b": "Option B",
      "c": "Option C",
      "d": "Option D"
    },
    "correct_answer": "b"
  }
]

⚠️ Do NOT include:
- Explanations
- Headings
- Markdown
- Backticks
- Any text outside JSON
"""

# --- TOPIC BASED SYSTEM PROMPT (MODERATE / MIXED) ---
TOPIC_SYSTEM_PROMPT = """
You are a SENIOR EXAM PAPER SETTER for the Allahabad High Court (RO/ARO/APS Exams).
Your task is to generate HIGH-QUALITY, EXAM-LEVEL MCQs based on the provided SUBJECT/TOPIC.

You MUST use your internal knowledge base to create factual, accurate, and challenging questions.
The questions should be suitable for a competitive exam in India.

━━━━━━━━━━━━━━━━━━━━━━
EXAM PATTERN TO FOLLOW
━━━━━━━━━━━━━━━━━━━━━━
Generate a MIX of:
1. Statement Based Questions (Consider the following statements...)
2. Match the Following (List I vs List II)
3. Chronological Order (Arrange events...)
4. Assertion-Reasoning (Assertion (A) / Reason (R))
5. Direct Factual Questions (Who/When/Where/Which Article...)

━━━━━━━━━━━━━━━━━━━━━━
MCQ STRUCTURE RULES
━━━━━━━━━━━━━━━━━━━━━━
- Exactly 4 options (a, b, c, d).
- ONLY ONE correct answer.
- Randomize correct answer positions.
- High difficulty level (Hard/Moderate).

━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT FORMAT (NO EXTRA TEXT)
━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON ARRAY:
[
  {
    "question": "Question text?",
    "options": { "a": "...", "b": "...", "c": "...", "d": "..." },
    "correct_answer": "a"
  }
]
"""

# --- TOPIC BASED SYSTEM PROMPT (EASY / ONE-LINER) ---
TOPIC_SYSTEM_PROMPT_EASY = """
You are a SENIOR EXAM PAPER SETTER for the Allahabad High Court (RO/ARO/APS Exams).
Your task is to generate HIGH-QUALITY, EXAM-LEVEL MCQs based on the provided SUBJECT/TOPIC.

You MUST use your internal knowledge base to create factual, accurate questions.

━━━━━━━━━━━━━━━━━━━━━━
EXAM PATTERN TO FOLLOW
━━━━━━━━━━━━━━━━━━━━━━
Generate ONLY:
1. Direct Factual Questions (One-Liners)
   - Dates, Articles, Sections, Books, Authors, Capitals, Scientific Names, etc.
   - Who/When/Where/Which type questions.
   
DO NOT generate:
- Statement based questions
- Match the following
- Chronological order
- Assertion-Reasoning

━━━━━━━━━━━━━━━━━━━━━━
MCQ STRUCTURE RULES
━━━━━━━━━━━━━━━━━━━━━━
- Exactly 4 options (a, b, c, d).
- ONLY ONE correct answer.
- Randomize correct answer positions.
- Difficulty Level: EASY/MODERATE (Fact based).

━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT FORMAT (NO EXTRA TEXT)
━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON ARRAY:
[
  {
    "question": "Question text?",
    "options": { "a": "...", "b": "...", "c": "...", "d": "..." },
    "correct_answer": "a"
  }
]
"""

# --- TOPIC BASED SYSTEM PROMPT (EASY-TO-MODERATE / DEEP ONE-LINER) ---
TOPIC_SYSTEM_PROMPT_EASY_TO_MODERATE = """
You are a SENIOR EXAM PAPER SETTER for the Allahabad High Court (RO/ARO/APS Exams) and UPPSC/SSC exams.
Your task is to generate HIGH-QUALITY, COMPETITIVE EXAM-LEVEL MCQs based on the provided SUBJECT/TOPIC.

You MUST use your internal knowledge base to create questions that test CONCEPTUAL CLARITY and APPLICATION, not just rote memorization.
The style should match Previous Year Questions (PYQs) of SSC, UPSSC, Junior Assistant, and Lower PCS exams.

━━━━━━━━━━━━━━━━━━━━━━
EXAM PATTERN TO FOLLOW
━━━━━━━━━━━━━━━━━━━━━━
Generate "EASY-TO-MODERATE" level questions with the following characteristics:
1. DEEP ONE-LINERS:
   - Questions should be one-liners but NOT simple surface-level facts.
   - They must require understanding of the concept or logic to answer.
   - Avoid "Spoon-feeding" facts (e.g., instead of "When was X born?", ask "Which event led to the rise of X?").

2. LOGICAL & CONCEPTUAL:
   - Mix of Concept + Application + Elimination logic.
   - Questions where options are close or require distinct knowledge to eliminate.

3. DOMAINS:
   - Use style from: SSC, UPSSC, Junior Assistant, Lower PCS.

DO NOT generate:
- Complex multi-statement questions (like "Consider statements 1, 2, 3...").
- Match the following lists (keep it to single question format).
- Simple, trivial facts that are too easy.

━━━━━━━━━━━━━━━━━━━━━━
MCQ STRUCTURE RULES
━━━━━━━━━━━━━━━━━━━━━━
- Exactly 4 options (a, b, c, d).
- ONLY ONE correct answer.
- Randomize correct answer positions.
- Options should be plausible distractors.

━━━━━━━━━━━━━━━━━━━━━━
STRICT OUTPUT FORMAT (NO EXTRA TEXT)
━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a valid JSON ARRAY:
[
  {
    "question": "Question text?",
    "options": { "a": "...", "b": "...", "c": "...", "d": "..." },
    "correct_answer": "a"
  }
]
"""

# Configure Gemini API
def get_gemini_model(system_prompt=SYSTEM_PROMPT):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "your_gemini_api_key_here" in api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name='gemini-2.0-flash',
        system_instruction=system_prompt
    )

def chunk_text(text: str, max_chars: int = 4000) -> Generator[str, None, None]:
    """Yields chunks of text. Respects page boundaries if present."""
    if "<<<PAGE_BREAK>>>" in text:
        pages = text.split("<<<PAGE_BREAK>>>")
        for page in pages:
            if not page.strip():
                continue
            # If page is too big, chunk it further
            if len(page) > max_chars:
                for i in range(0, len(page), max_chars):
                    yield page[i:i+max_chars]
            else:
                yield page
    else:
        for i in range(0, len(text), max_chars):
            yield text[i:i+max_chars]

def clean_json_response(text: str) -> str:
    """Extracts JSON array from response text."""
    text = text.strip()
    # Remove markdown code blocks
    if "```json" in text:
        text = text.replace("```json", "").replace("```", "")
    elif "```" in text:
        text = text.replace("```", "")
    
    # Find start and end of list
    start = text.find('[')
    end = text.rfind(']')
    
    if start != -1 and end != -1:
        return text[start:end+1]
    return text

def validate_mcq(item: dict) -> bool:
    """Validates MCQ structure."""
    required_keys = ["question", "options", "correct_answer"]
    if not all(key in item for key in required_keys):
        return False
    if not isinstance(item["options"], dict):
        return False
    if not all(k in item["options"] for k in ["a", "b", "c", "d"]):
        return False
    return True

def generate_mcqs_from_text(text: str, total_questions: int = 10, difficulty: str = "hard") -> List[McqItem]:
    """
    Generates MCQs from provided text using Gemini.
    """
    model = get_gemini_model(SYSTEM_PROMPT)
    if not model:
        raise ValueError("Gemini API Key is missing or invalid.")

    mcqs = []
    chunks = list(chunk_text(text))
    
    if not chunks:
        return []

    # Calculate questions per chunk
    questions_per_chunk = max(1, -(-total_questions // len(chunks))) # Ceiling division
    
    print(f"Generating {total_questions} MCQs from {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        if len(mcqs) >= total_questions:
            break
            
        remaining = total_questions - len(mcqs)
        current_batch_size = min(remaining, questions_per_chunk)
        
        prompt = f"""
        CONTEXT TEXT:
        {chunk}
        
        TASK:
        Generate {current_batch_size} unique MCQs from the text above.
        Difficulty Level: {difficulty.upper()}
        """
        
        try:
            response = model.generate_content(prompt)
            json_str = clean_json_response(response.text)
            data = json.loads(json_str)
            
            for item in data:
                if validate_mcq(item):
                    mcqs.append(McqItem(**item))
                    
            time.sleep(1) # Rate limiting
            
        except Exception as e:
            print(f"Error processing chunk {i}: {e}")
            continue

    return mcqs[:total_questions]

def generate_mcqs_from_topic(
    topic: str,
    count: int,
    difficulty_mode: str = "moderate",
    sub_topics: List[str] = None,
    extra_instructions: Optional[str] = None,
) -> List[McqItem]:
    """
    Generates MCQs from a Topic/Subject using internal knowledge.
    difficulty_mode: 'easy', 'moderate', or 'easy-to-moderate'.
    sub_topics: Optional list of specific sub-topics to focus on.
    """
    # Select System Prompt based on Difficulty Mode
    if difficulty_mode == "easy":
        system_prompt = TOPIC_SYSTEM_PROMPT_EASY
        diff_label = "EASY (ONE-LINER FACTUAL)"
    elif difficulty_mode == "easy-to-moderate":
        system_prompt = TOPIC_SYSTEM_PROMPT_EASY_TO_MODERATE
        diff_label = "EASY-TO-MODERATE (DEEP CONCEPTUAL ONE-LINERS)"
    else:
        system_prompt = TOPIC_SYSTEM_PROMPT
        diff_label = "MODERATE (MIXED TYPES)"

    model = get_gemini_model(system_prompt)
    if not model:
        raise ValueError("Gemini API Key is missing or invalid.")

    mcqs = []
    retries = 0
    max_retries = 3
    
    while len(mcqs) < count and retries < max_retries:
        needed = count - len(mcqs)
        # Request slightly more to account for bad formatting
        request_count = needed + 2
        
        sub_topic_str = ""
        if sub_topics:
            import random
            # Select a random subset of sub-topics to ensure diversity in this batch
            selected_subs = random.sample(sub_topics, min(len(sub_topics), 5))
            sub_topic_str = f"\n        Focus on these specific sub-topics: {', '.join(selected_subs)}"

        # Add Hindi instruction if the topic is "General Hindi"
        language_instruction = ""
        if "hindi" in topic.lower():
            language_instruction = """
            IMPORTANT: The Subject is 'General Hindi'. 
            You MUST generate the Questions, Options, and Answers in HINDI LANGUAGE (Devanagari Script).
            Ensure correct Hindi grammar and vocabulary suitable for competitive exams.
            """

        print(f"Generating {needed} MCQs for topic: {topic} ({diff_label})...")
        
        prompt = f"""
        SUBJECT: {topic}
        {sub_topic_str}
        
        TASK:
        Generate {request_count} high-quality unique MCQs strictly related to {topic}.
        Mode: {diff_label}
        {language_instruction}
        {extra_instructions or ""}
        
        Ensure diverse sub-topics within {topic}.
        """
        
        try:
            response = model.generate_content(prompt)
            json_str = clean_json_response(response.text)
            data = json.loads(json_str)
            
            valid_items = []
            for item in data:
                if validate_mcq(item):
                    # Check for duplicates within this batch or existing
                    is_dup = False
                    for existing in mcqs:
                        if existing.question == item['question']:
                            is_dup = True
                            break
                    if not is_dup:
                        valid_items.append(McqItem(**item))
            
            mcqs.extend(valid_items)
            
            if len(mcqs) < count:
                retries += 1
                time.sleep(1)
            else:
                break
                
        except Exception as e:
            print(f"Error generating from topic {topic}: {e}")
            retries += 1
            time.sleep(2)

    return mcqs[:count]


TRANSLATE_MCQS_TO_HINDI_SYSTEM_PROMPT = """
You are a professional translator for competitive exam content.

INPUT: A JSON array of MCQs in English in this exact structure:
[
  {
    "question": "...",
    "options": { "a": "...", "b": "...", "c": "...", "d": "..." },
    "correct_answer": "a"
  }
]

TASK:
- Translate ONLY the "question" and "options" text into Hindi (Devanagari).
- Ensure the output is PURE HINDI: do not leave English words. If a proper noun is commonly used in English,
  translate it to the standard Hindi form or transliterate it into Devanagari (e.g., "Ashoka" -> "अशोक").
- Keep numbers/years as digits (e.g., 1857, 2020) unless the original explicitly uses words.
- Do NOT change the JSON structure.
- Do NOT change option keys (a/b/c/d).
- Do NOT change "correct_answer" letter.
- Keep meaning accurate and exam-style.

OUTPUT: Return ONLY a valid JSON array (no markdown, no extra text).
"""


def translate_mcqs_to_hindi(mcqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or "your_gemini_api_key_here" in api_key:
        raise ValueError("Gemini API Key is missing or invalid.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config={"temperature": 0.1},
        system_instruction=TRANSLATE_MCQS_TO_HINDI_SYSTEM_PROMPT,
    )

    translated: List[Dict[str, Any]] = []
    batch_size = 10
    for i in range(0, len(mcqs), batch_size):
        batch = mcqs[i : i + batch_size]
        prompt = json.dumps(batch, ensure_ascii=False)

        response = model.generate_content(prompt)
        try:
            arr = json.loads(clean_json_response(response.text))
            if isinstance(arr, list):
                translated.extend(arr)
                continue
        except Exception:
            pass

        parsed = safe_json_parse(response.text)
        arr2 = parsed.get("array")
        if isinstance(arr2, list):
            translated.extend(arr2)
            continue

        raise ValueError("Failed to translate MCQs to Hindi (invalid model output).")

    return translated[: len(mcqs)]
