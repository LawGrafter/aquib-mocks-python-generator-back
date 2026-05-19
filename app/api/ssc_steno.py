from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, List, Optional
import pandas as pd
import uuid
import os
import io
import random
from rapidfuzz import fuzz
from app.services import mcq_service
from app.utils.file_manager import write_csv

router = APIRouter()


class AIEditRequest(BaseModel):
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    prompt: str
    subject: Optional[str] = ""
    topic: Optional[str] = ""


@router.post("/ssc-steno/ai-edit")
async def ai_edit_question(req: AIEditRequest):
    """Use AI to modify a question based on a user prompt."""
    import json as _json
    import google.generativeai as genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction="You are an expert exam question editor for SSC Stenographer exam. Return ONLY valid JSON."
    )

    edit_prompt = f"""You are editing an MCQ question for an SSC Stenographer exam.

CURRENT QUESTION:
Question: {req.question}
Option A: {req.option_a}
Option B: {req.option_b}
Option C: {req.option_c}
Option D: {req.option_d}
Correct Answer: {req.correct_answer}
Subject: {req.subject}
Topic: {req.topic}

USER INSTRUCTION: {req.prompt}

Please modify the question according to the user's instruction. Keep the same format.
Return ONLY a valid JSON object (no markdown, no backticks):
{{"question": "...", "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "correct_answer": "a/b/c/d"}}
"""

    try:
        response = model.generate_content(edit_prompt)
        json_str = mcq_service.clean_json_response(response.text)
        result = _json.loads(json_str)
        return {
            "question": result.get("question", req.question),
            "option_a": result.get("option_a", req.option_a),
            "option_b": result.get("option_b", req.option_b),
            "option_c": result.get("option_c", req.option_c),
            "option_d": result.get("option_d", req.option_d),
            "correct_answer": result.get("correct_answer", req.correct_answer),
        }
    except Exception as e:
        print(f"AI Edit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# SSC Stenographer 2026 Syllabus - Exact breakdown (200 total)
# ============================================================
SSC_STENO_SYLLABUS = {
    # PART I: General Intelligence & Reasoning (50 questions)
    "Analogy": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Word Analogy", "count": 1},
            {"type": "Number Analogy", "count": 1},
            {"type": "Letter Analogy", "count": 1}
        ]
    },
    "Similarities & Differences": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Odd One Out (Word)", "count": 1},
            {"type": "Odd One Out (Number)", "count": 1},
            {"type": "Classification", "count": 1}
        ]
    },
    "Space Visualization": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Mirror Image", "count": 1},
            {"type": "Water Image", "count": 1},
            {"type": "Paper Folding / Cutting", "count": 1}
        ]
    },
    "Problem Solving": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Mathematical Operations", "count": 1},
            {"type": "Missing Number", "count": 1},
            {"type": "Logical Problem", "count": 1}
        ]
    },
    "Analysis & Judgement": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Statement & Conclusion", "count": 1},
            {"type": "Statement & Assumption", "count": 1},
            {"type": "Logical Deduction", "count": 1}
        ]
    },
    "Decision Making": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Situation-based Decision", "count": 1},
            {"type": "Course of Action", "count": 1},
            {"type": "Cause & Effect", "count": 1}
        ]
    },
    "Visual Memory": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Figure Series Completion", "count": 1},
            {"type": "Pattern Recognition", "count": 1},
            {"type": "Embedded Figure", "count": 1}
        ]
    },
    "Discriminating Observation": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Figure Counting", "count": 1},
            {"type": "Dot Situation", "count": 1},
            {"type": "Grouping of Identical Figures", "count": 1}
        ]
    },
    "Coding-Decoding": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Letter Coding", "count": 1},
            {"type": "Number Coding", "count": 1},
            {"type": "Mixed Coding", "count": 1}
        ]
    },
    "Puzzle": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Seating Arrangement", "count": 1},
            {"type": "Floor-based Puzzle", "count": 1},
            {"type": "Scheduling Puzzle", "count": 1}
        ]
    },
    "Venn Diagram": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Three Element Venn Diagram", "count": 2},
            {"type": "Logical Venn Diagram", "count": 1}
        ]
    },
    "Direction & Distance": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Direction Sense", "count": 2},
            {"type": "Distance Calculation", "count": 1}
        ]
    },
    "Blood Relation": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Direct Blood Relation", "count": 2},
            {"type": "Coded Blood Relation", "count": 1}
        ]
    },
    "Order & Ranking": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Linear Arrangement", "count": 1},
            {"type": "Position from Top/Bottom", "count": 1},
            {"type": "Comparison-based Ranking", "count": 1}
        ]
    },
    "Number Series": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Missing Number in Series", "count": 1},
            {"type": "Wrong Number in Series", "count": 1},
            {"type": "Alphabet/Alpha-Numeric Series", "count": 1}
        ]
    },
    "Verbal Reasoning": {
        "part": "General Intelligence & Reasoning",
        "count": 2,
        "breakdown": [
            {"type": "Syllogism", "count": 1},
            {"type": "Inequality / Mathematical Comparison", "count": 1}
        ]
    },
    "Non-Verbal Reasoning": {
        "part": "General Intelligence & Reasoning",
        "count": 3,
        "breakdown": [
            {"type": "Figure Matrix", "count": 1},
            {"type": "Rule Detection", "count": 1},
            {"type": "Dice / Cube", "count": 1}
        ]
    },

    # PART II: General Awareness (50 questions)
    "Static Awareness": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "First/Largest/Longest in India & World", "count": 2},
            {"type": "Important Headquarters / Organizations", "count": 1},
            {"type": "National Symbols / Emblems", "count": 1},
            {"type": "Awards & Honours", "count": 1}
        ]
    },
    "Current Affairs": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Government Schemes & Policies 2025-26", "count": 2},
            {"type": "Important Appointments & Events 2025-26", "count": 2},
            {"type": "International Summits & Agreements", "count": 1}
        ]
    },
    "Science & Technology": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Inventions & Discoveries", "count": 2},
            {"type": "Space & Defence Technology", "count": 1},
            {"type": "Diseases & Nutrition", "count": 1},
            {"type": "Scientific Instruments", "count": 1}
        ]
    },
    "History": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Ancient India (Indus Valley, Vedic Period)", "count": 1},
            {"type": "Medieval India (Mughal, Delhi Sultanate)", "count": 1},
            {"type": "Modern India (Freedom Movement, Acts)", "count": 2},
            {"type": "World History", "count": 1}
        ]
    },
    "Culture": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Indian Dance Forms", "count": 1},
            {"type": "Festivals & Traditions", "count": 1},
            {"type": "Famous Temples / Monuments", "count": 1},
            {"type": "Art & Literature", "count": 1},
            {"type": "UNESCO World Heritage Sites in India", "count": 1}
        ]
    },
    "Geography": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Indian Rivers & Lakes", "count": 1},
            {"type": "Mountains & Passes", "count": 1},
            {"type": "Climate & Soil Types", "count": 1},
            {"type": "World Geography (Continents, Oceans)", "count": 1},
            {"type": "Indian States & Boundaries", "count": 1}
        ]
    },
    "Economic Scene": {
        "part": "General Awareness",
        "count": 4,
        "breakdown": [
            {"type": "Indian Economy Basics (GDP, Inflation)", "count": 1},
            {"type": "Banking & Finance (RBI, Fiscal Policy)", "count": 1},
            {"type": "Five Year Plans / NITI Aayog", "count": 1},
            {"type": "Budget & Taxation", "count": 1}
        ]
    },
    "General Polity": {
        "part": "General Awareness",
        "count": 5,
        "breakdown": [
            {"type": "Indian Constitution Articles & Schedules", "count": 2},
            {"type": "Fundamental Rights & Duties", "count": 1},
            {"type": "Parliament & State Legislature", "count": 1},
            {"type": "Panchayati Raj & Local Governance", "count": 1}
        ]
    },
    "Scientific Research": {
        "part": "General Awareness",
        "count": 4,
        "breakdown": [
            {"type": "ISRO / Space Missions", "count": 1},
            {"type": "DRDO / Defence Research", "count": 1},
            {"type": "Medical / Biotech Research", "count": 1},
            {"type": "Nuclear / Atomic Energy", "count": 1}
        ]
    },
    "Indian Constitution": {
        "part": "General Awareness",
        "count": 4,
        "breakdown": [
            {"type": "Constitutional Amendments", "count": 1},
            {"type": "Emergency Provisions", "count": 1},
            {"type": "Directive Principles", "count": 1},
            {"type": "Constitutional Bodies (Election Commission, CAG)", "count": 1}
        ]
    },
    "Sports": {
        "part": "General Awareness",
        "count": 3,
        "breakdown": [
            {"type": "Cricket / Olympics / Commonwealth", "count": 1},
            {"type": "Trophies & Tournaments", "count": 1},
            {"type": "Famous Sports Personalities", "count": 1}
        ]
    },

    # PART III: English Language & Comprehension (100 questions)
    "Reading Comprehension": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Passage-based Factual Question", "count": 4},
            {"type": "Passage-based Inference Question", "count": 3},
            {"type": "Passage Title / Main Idea", "count": 3}
        ]
    },
    "Synonyms & Antonyms": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Synonym", "count": 5},
            {"type": "Antonym", "count": 5}
        ]
    },
    "Fill in the Blanks": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Single Blank (Vocabulary)", "count": 5},
            {"type": "Single Blank (Grammar/Preposition)", "count": 5}
        ]
    },
    "Spellings": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Correctly Spelt Word", "count": 5},
            {"type": "Incorrectly Spelt Word", "count": 5}
        ]
    },
    "Phrases & Idiom Meaning": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Idiom Meaning", "count": 5},
            {"type": "Phrase Meaning", "count": 5}
        ]
    },
    "Active & Passive Voice": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Active to Passive Conversion", "count": 5},
            {"type": "Passive to Active Conversion", "count": 5}
        ]
    },
    "Direct & Indirect Speech": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Direct to Indirect Speech", "count": 5},
            {"type": "Indirect to Direct Speech", "count": 5}
        ]
    },
    "Para Jumble & Sentence Jumble": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Para Jumble (Rearrange Sentences)", "count": 5},
            {"type": "Sentence Rearrangement (Word Order)", "count": 5}
        ]
    },
    "Sentence Correction": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Phrase Replacement", "count": 5},
            {"type": "Sentence Improvement", "count": 5}
        ]
    },
    "Error Spotting": {
        "part": "English Language & Comprehension",
        "count": 10,
        "breakdown": [
            {"type": "Spot the Error (Grammar)", "count": 5},
            {"type": "Spot the Error (Vocabulary/Usage)", "count": 5}
        ]
    }
}

TOTAL_QUESTIONS = 200


class SSCStenoResponse(BaseModel):
    total_generated: int
    final_count: int
    csv_url: str
    breakdown: Dict[str, int]
    duplicates_removed: int = 0


# ============================================
# Question type format instructions
# ============================================
TYPE_FORMAT_MAP = {
    # Reasoning types
    "Word Analogy": "Give a pair of related words and ask to find the analogous pair. 4 options.",
    "Number Analogy": "Give a number pair relationship and ask to find the analogous number. 4 options.",
    "Letter Analogy": "Give a letter pair relationship and ask to find the analogous letter group. 4 options.",
    "Odd One Out (Word)": "Give 4 words, ask which one is different from the rest.",
    "Odd One Out (Number)": "Give 4 numbers, ask which one doesn't belong to the pattern.",
    "Classification": "Give 4 items and ask which does not belong to the group.",
    "Mirror Image": "Describe a figure and ask what its mirror image would look like. 4 options.",
    "Water Image": "Describe a figure and ask what its water reflection would look like. 4 options.",
    "Paper Folding / Cutting": "Describe a paper folding and cutting scenario, ask for the unfolded result. 4 options.",
    "Mathematical Operations": "Replace mathematical symbols and solve. 4 options.",
    "Missing Number": "Give a number pattern/matrix with a missing number. 4 options.",
    "Logical Problem": "A logic-based word problem requiring deduction. 4 options.",
    "Statement & Conclusion": "Give a statement and ask which conclusion logically follows. 4 options.",
    "Statement & Assumption": "Give a statement and ask which assumption is implicit. 4 options.",
    "Logical Deduction": "Give premises and ask what can be logically deduced. 4 options.",
    "Situation-based Decision": "Describe a situation and ask the best course of action. 4 options.",
    "Course of Action": "Give a problem statement and ask which course of action is appropriate. 4 options.",
    "Cause & Effect": "Give two statements and ask which is cause and which is effect. 4 options.",
    "Figure Series Completion": "Describe a series of figures and ask what comes next. 4 options.",
    "Pattern Recognition": "Describe a visual pattern and ask to identify it. 4 options.",
    "Embedded Figure": "Ask which figure is embedded within a given complex figure. 4 options.",
    "Figure Counting": "Ask how many triangles/squares/lines in a given figure. 4 options.",
    "Dot Situation": "Ask about position of a dot with respect to geometric shapes. 4 options.",
    "Grouping of Identical Figures": "Ask to group identical figures from a set. 4 options.",
    "Letter Coding": "Give a letter-based coding rule and ask to code/decode. 4 options.",
    "Number Coding": "Give a number-based coding rule and ask to code/decode. 4 options.",
    "Mixed Coding": "Give a mixed letter-number coding rule. 4 options.",
    "Seating Arrangement": "Describe a seating arrangement and ask a question about positions. 4 options.",
    "Floor-based Puzzle": "People live on different floors, ask who lives where. 4 options.",
    "Scheduling Puzzle": "Give scheduling constraints and ask a deduction question. 4 options.",
    "Three Element Venn Diagram": "Describe three overlapping sets and ask a question. 4 options.",
    "Logical Venn Diagram": "Ask which Venn diagram represents the relationship between 3 items. 4 options.",
    "Direction Sense": "Give a series of direction-based movements and ask final direction. 4 options.",
    "Distance Calculation": "Give direction movements with distances and ask total distance/displacement. 4 options.",
    "Direct Blood Relation": "Describe family relationships and ask how two people are related. 4 options.",
    "Coded Blood Relation": "Use coded symbols for relationships and ask to decode. 4 options.",
    "Linear Arrangement": "People standing in a line, ask position-based question. 4 options.",
    "Position from Top/Bottom": "Give rank from top and bottom, ask total or position. 4 options.",
    "Comparison-based Ranking": "Compare multiple items and ask about ranking. 4 options.",
    "Missing Number in Series": "Give a number series with a blank, ask for the missing number. 4 options.",
    "Wrong Number in Series": "Give a number series with one wrong number, ask to find it. 4 options.",
    "Alphabet/Alpha-Numeric Series": "Give a letter/alphanumeric series, ask for next term. 4 options.",
    "Syllogism": "Give two or more premises and ask which conclusion follows. 4 options.",
    "Inequality / Mathematical Comparison": "Give coded inequality expressions and ask valid conclusions. 4 options.",
    "Figure Matrix": "A 3x3 matrix of figures with one missing, ask for the correct figure. 4 options.",
    "Rule Detection": "Show a set of figures following a rule, ask to identify the rule. 4 options.",
    "Dice / Cube": "Show different faces of a dice/cube, ask what is opposite to a face. 4 options.",

    # GA types
    "First/Largest/Longest in India & World": "Ask about firsts, largest, longest, etc. in India or the world. 4 options.",
    "Important Headquarters / Organizations": "Ask about HQ locations of national/international organizations. 4 options.",
    "National Symbols / Emblems": "Ask about India's national symbols, emblems, animals, etc. 4 options.",
    "Awards & Honours": "Ask about recipients of Padma Awards, Nobel Prize, Bharat Ratna, etc. 4 options.",
    "Government Schemes & Policies 2025-26": "Ask about recent government schemes launched in 2025-26. 4 options.",
    "Important Appointments & Events 2025-26": "Ask about recent appointments, events in 2025-26. 4 options.",
    "International Summits & Agreements": "Ask about G20, BRICS, or bilateral agreements. 4 options.",
    "Inventions & Discoveries": "Ask who invented/discovered what. 4 options.",
    "Space & Defence Technology": "Ask about recent space missions, defence tech. 4 options.",
    "Diseases & Nutrition": "Ask about diseases, vitamins, nutrition facts. 4 options.",
    "Scientific Instruments": "Ask about instruments and their uses. 4 options.",
    "Ancient India (Indus Valley, Vedic Period)": "Ask about Indus Valley civilization, Vedic period facts. 4 options.",
    "Medieval India (Mughal, Delhi Sultanate)": "Ask about Mughal or Delhi Sultanate rulers, events. 4 options.",
    "Modern India (Freedom Movement, Acts)": "Ask about Indian freedom struggle, important acts. 4 options.",
    "World History": "Ask about important world history events, revolutions. 4 options.",
    "Indian Dance Forms": "Ask about classical dance forms and their states. 4 options.",
    "Festivals & Traditions": "Ask about Indian festivals, when and where celebrated. 4 options.",
    "Famous Temples / Monuments": "Ask about famous temples, monuments, their locations. 4 options.",
    "Art & Literature": "Ask about famous books, authors, literary works. 4 options.",
    "UNESCO World Heritage Sites in India": "Ask about UNESCO sites in India. 4 options.",
    "Indian Rivers & Lakes": "Ask about rivers, their origins, tributaries, lakes. 4 options.",
    "Mountains & Passes": "Ask about mountain ranges, passes in India. 4 options.",
    "Climate & Soil Types": "Ask about Indian climate zones, soil types. 4 options.",
    "World Geography (Continents, Oceans)": "Ask about continents, oceans, countries. 4 options.",
    "Indian States & Boundaries": "Ask about Indian state boundaries, capitals. 4 options.",
    "Indian Economy Basics (GDP, Inflation)": "Ask about GDP, inflation, economic indicators. 4 options.",
    "Banking & Finance (RBI, Fiscal Policy)": "Ask about RBI policies, banking terms. 4 options.",
    "Five Year Plans / NITI Aayog": "Ask about five year plans, NITI Aayog initiatives. 4 options.",
    "Budget & Taxation": "Ask about Union Budget, GST, taxation. 4 options.",
    "Indian Constitution Articles & Schedules": "Ask about specific articles and schedules. 4 options.",
    "Fundamental Rights & Duties": "Ask about fundamental rights, duties. 4 options.",
    "Parliament & State Legislature": "Ask about Lok Sabha, Rajya Sabha, state legislatures. 4 options.",
    "Panchayati Raj & Local Governance": "Ask about 73rd/74th amendment, local governance. 4 options.",
    "ISRO / Space Missions": "Ask about ISRO missions, Chandrayaan, Gaganyaan. 4 options.",
    "DRDO / Defence Research": "Ask about DRDO projects, missiles. 4 options.",
    "Medical / Biotech Research": "Ask about medical breakthroughs, biotech. 4 options.",
    "Nuclear / Atomic Energy": "Ask about nuclear power plants, atomic energy. 4 options.",
    "Constitutional Amendments": "Ask about important constitutional amendments. 4 options.",
    "Emergency Provisions": "Ask about types of emergencies in constitution. 4 options.",
    "Directive Principles": "Ask about DPSP and their categories. 4 options.",
    "Constitutional Bodies (Election Commission, CAG)": "Ask about constitutional bodies and their roles. 4 options.",
    "Cricket / Olympics / Commonwealth": "Ask about recent sports events, winners. 4 options.",
    "Trophies & Tournaments": "Ask about famous trophies and associated sports. 4 options.",
    "Famous Sports Personalities": "Ask about sports personalities and their achievements. 4 options.",

    # English types
    "Passage-based Factual Question": "Give a passage and ask a factual question based on it. 4 options.",
    "Passage-based Inference Question": "Give a passage and ask an inference-based question. 4 options.",
    "Passage Title / Main Idea": "Give a passage and ask for the best title or main idea. 4 options.",
    "Synonym": "Choose the word most similar in meaning. 4 options.",
    "Antonym": "Choose the word most opposite in meaning. 4 options.",
    "Single Blank (Vocabulary)": "Fill in the blank with the most appropriate word (vocabulary). 4 options.",
    "Single Blank (Grammar/Preposition)": "Fill in the blank with the correct grammar/preposition. 4 options.",
    "Correctly Spelt Word": "Which of the following words is correctly spelt? 4 options.",
    "Incorrectly Spelt Word": "Which of the following words is incorrectly spelt? 4 options.",
    "Idiom Meaning": "Give an idiom and ask for its meaning. 4 options.",
    "Phrase Meaning": "Give a phrase and ask for its meaning. 4 options.",
    "Active to Passive Conversion": "Convert the given sentence from active to passive voice. 4 options.",
    "Passive to Active Conversion": "Convert the given sentence from passive to active voice. 4 options.",
    "Direct to Indirect Speech": "Convert direct speech to indirect speech. 4 options.",
    "Indirect to Direct Speech": "Convert indirect speech to direct speech. 4 options.",
    "Para Jumble (Rearrange Sentences)": "Rearrange jumbled sentences to form a coherent paragraph. 4 options.",
    "Sentence Rearrangement (Word Order)": "Rearrange jumbled words to form a meaningful sentence. 4 options.",
    "Phrase Replacement": "Replace the underlined phrase with a correct alternative. 4 options.",
    "Sentence Improvement": "Improve the underlined part of the sentence. 4 options.",
    "Spot the Error (Grammar)": "Find the part of the sentence that contains a grammatical error. 4 options (a/b/c/d parts).",
    "Spot the Error (Vocabulary/Usage)": "Find the part with incorrect word usage. 4 options (a/b/c/d parts)."
}


def _get_type_instruction(question_type):
    return TYPE_FORMAT_MAP.get(question_type, f"Generate an MCQ of type '{question_type}'. 4 options.")


# ============================================
# Helper: Generate for a single type
# ============================================
def _generate_for_type(subject, question_type, count, difficulty, max_attempts=3):
    import json as _json
    import os as _os
    import time as _time
    import google.generativeai as genai

    api_key = _os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction="You are an expert exam setter for SSC Stenographer Grade C & D exam. Return ONLY valid JSON."
    )

    instruction = _get_type_instruction(question_type)

    prompt = f"""Generate exactly {count} MCQ(s) for SSC Stenographer exam.
Subject: {subject}
Type: {question_type}
Difficulty: {difficulty.upper()}

FORMAT: {instruction}

RETURN a valid JSON array of {count} MCQ objects.
Each object: {{"question": "...", "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}}, "correct_answer": "a", "question_type": "{question_type}"}}
Return ONLY the JSON array. No markdown, no backticks, no extra text."""

    results = []
    for attempt in range(max_attempts):
        try:
            response = model.generate_content(prompt)
            json_str = mcq_service.clean_json_response(response.text)
            data = _json.loads(json_str)

            for mcq_item in data:
                if mcq_service.validate_mcq(mcq_item):
                    mcq_item["Subject"] = subject
                    mcq_item["Question_Type"] = question_type
                    mcq_item["Difficulty"] = difficulty
                    results.append(mcq_item)

            if results:
                break
        except Exception as e:
            print(f"  ⚠️ Attempt {attempt+1}/{max_attempts} failed for {subject}/{question_type}: {e}")
            _time.sleep(1)

    return results[:count]


# ============================================
# Helper: Generate batch for a subject
# ============================================
def _generate_subject_batch(subject, details, difficulty):
    import json as _json
    import os as _os
    import time as _time
    import google.generativeai as genai

    total = details['count']
    type_lines = []
    type_instructions = []
    for item in details['breakdown']:
        type_lines.append(f"- {item['type']}: {item['count']} question(s)")
        instruction = _get_type_instruction(item['type'])
        type_instructions.append(f"[{item['type']}]: {instruction}")

    combined_prompt = f"""SUBJECT: {subject}
EXAM: SSC Stenographer Grade C & D
DIFFICULTY: {difficulty.upper()}
TOTAL QUESTIONS NEEDED: {total}

Generate exactly {total} MCQs for \"{subject}\" with the following type breakdown:
{chr(10).join(type_lines)}

FORMAT INSTRUCTIONS PER TYPE:
{chr(10).join(type_instructions)}

RETURN a single valid JSON array of {total} MCQ objects.
Each object: {{"question": "...", "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}}, "correct_answer": "a", "question_type": "the type from the breakdown above"}}
Return ONLY the JSON array. No markdown, no backticks, no extra text.
"""

    api_key = _os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction="You are an expert exam setter for SSC Stenographer Grade C & D exam. Return ONLY valid JSON."
    )

    results = []
    for attempt in range(3):
        try:
            response = model.generate_content(combined_prompt)
            json_str = mcq_service.clean_json_response(response.text)
            data = _json.loads(json_str)

            for mcq_item in data:
                if mcq_service.validate_mcq(mcq_item):
                    mcq_dict = mcq_item
                    mcq_dict["Subject"] = subject
                    mcq_dict["Question_Type"] = mcq_item.get("question_type", "")
                    mcq_dict["Difficulty"] = difficulty
                    results.append(mcq_dict)

            if results:
                print(f"  ✅ Batch got {len(results)}/{total} questions")
                break
        except Exception as e:
            print(f"  ⚠️ Batch attempt {attempt+1}/3 failed: {e}")
            _time.sleep(1)

    return results[:total]


# ============================================
# Helper: Parse existing CSVs for dedup
# ============================================
def _parse_existing_csvs(csv_bytes_list):
    existing = []
    for raw in csv_bytes_list:
        try:
            text = raw.decode('utf-8', errors='ignore')
            df = pd.read_csv(io.StringIO(text))
            for _, row in df.iterrows():
                q = str(row.get('Question', '')).strip()
                if q:
                    existing.append(q)
        except Exception as e:
            print(f"  ⚠️ Failed to parse a CSV: {e}")
    return existing


def _dedup_against_existing(mcqs, existing_questions, threshold=80):
    unique = []
    removed = 0
    for mcq in mcqs:
        q = mcq.get('question', '')
        is_dup = False
        for eq in existing_questions:
            if fuzz.token_sort_ratio(q.lower(), eq.lower()) >= threshold:
                is_dup = True
                break
        if is_dup:
            removed += 1
        else:
            unique.append(mcq)
    return unique, removed


# ============================================
# ENDPOINT: Generate Custom SSC Steno
# ============================================
@router.post("/ssc-steno/generate-custom")
async def generate_ssc_steno_custom(
    difficulty: str = Form("moderate"),
    subjects: str = Form(""),
    total_questions: int = Form(10),
    previous_csvs: List[UploadFile] = File(default=[]),
):
    """Generate a CUSTOM SSC Steno exam for selected subjects with a specified question count."""
    import json as _json, math

    selected = [s.strip() for s in subjects.split(",") if s.strip()]
    if not selected:
        raise HTTPException(status_code=400, detail="No subjects selected")

    valid_subjects = {s: d for s, d in SSC_STENO_SYLLABUS.items() if s in selected}
    if not valid_subjects:
        raise HTTPException(status_code=400, detail="None of the provided subjects match the syllabus")

    raw_weights = {s: d["count"] for s, d in valid_subjects.items()}
    weight_sum = sum(raw_weights.values())
    distribution = {}
    allocated = 0
    subjects_list = list(valid_subjects.keys())
    for s in subjects_list[:-1]:
        count = max(1, round(total_questions * raw_weights[s] / weight_sum))
        distribution[s] = count
        allocated += count
    distribution[subjects_list[-1]] = max(1, total_questions - allocated)

    print(f"\n{'='*60}")
    print(f"  SSC Steno Custom Generation")
    print(f"  Difficulty: {difficulty.upper()}  |  Total: {total_questions}")
    print(f"  Subjects: {', '.join(selected)}")
    print(f"  Distribution: {distribution}")
    print(f"{'='*60}")

    existing_questions = []
    if previous_csvs:
        csv_bytes = []
        for f in previous_csvs:
            if f.filename:
                raw = await f.read()
                if raw:
                    csv_bytes.append(raw)
        if csv_bytes:
            existing_questions = _parse_existing_csvs(csv_bytes)

    all_mcqs = []
    breakdown = {}
    total_duplicates_removed = 0

    try:
        for subject, target_count in distribution.items():
            details = valid_subjects[subject]
            orig_total = details["count"]
            scaled_breakdown = []
            remaining = target_count
            for i, item in enumerate(details["breakdown"]):
                if i == len(details["breakdown"]) - 1:
                    cnt = remaining
                else:
                    cnt = max(1, round(target_count * item["count"] / orig_total))
                    cnt = min(cnt, remaining)
                remaining -= cnt
                if cnt > 0:
                    scaled_breakdown.append({"type": item["type"], "count": cnt})

            scaled_details = {"count": target_count, "breakdown": scaled_breakdown}
            print(f"\n📚 [{subject}] Generating {target_count} questions...")
            subject_mcqs = _generate_subject_batch(subject, scaled_details, difficulty)
            all_mcqs.extend(subject_mcqs)
            breakdown[subject] = len(subject_mcqs)
            print(f"  └─ Got {len(subject_mcqs)}/{target_count}")

        if existing_questions and all_mcqs:
            all_mcqs, total_duplicates_removed = _dedup_against_existing(all_mcqs, existing_questions)
            breakdown = {}
            for m in all_mcqs:
                subj = m.get("Subject", "Unknown")
                breakdown[subj] = breakdown.get(subj, 0) + 1

        top_up_round = 0
        while len(all_mcqs) < total_questions and top_up_round < 4:
            for subj in distribution:
                if len(all_mcqs) >= total_questions:
                    break
                details = valid_subjects[subj]
                qt = details["breakdown"][top_up_round % len(details["breakdown"])]["type"]
                fill = _generate_for_type(subj, qt, min(3, total_questions - len(all_mcqs)), difficulty, max_attempts=2)
                if existing_questions and fill:
                    fill, d = _dedup_against_existing(fill, existing_questions)
                    total_duplicates_removed += d
                all_mcqs.extend(fill)
                for m in fill:
                    breakdown[m.get("Subject", "Unknown")] = breakdown.get(m.get("Subject", "Unknown"), 0) + 1
            top_up_round += 1

        if not all_mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate any questions")

        all_mcqs = all_mcqs[:total_questions]

        def format_to_row(m_dict):
            return {
                "Subject": m_dict.get("Subject", ""),
                "Topic": m_dict.get("Question_Type", ""),
                "Question": m_dict["question"],
                "Option A": m_dict["options"]["a"],
                "Option B": m_dict["options"]["b"],
                "Option C": m_dict["options"]["c"],
                "Option D": m_dict["options"]["d"],
                "Correct Answer": m_dict["correct_answer"],
                "Points": 1,
            }

        rows = [format_to_row(m) for m in all_mcqs]
        df = pd.DataFrame(rows)

        filename_base = f"ssc_steno_custom_{difficulty}_{uuid.uuid4().hex[:8]}"
        write_csv(filename_base, df)
        csv_url = f"/exports/{filename_base}.csv"

        return SSCStenoResponse(
            total_generated=len(all_mcqs),
            final_count=len(all_mcqs),
            csv_url=csv_url,
            breakdown=breakdown,
            duplicates_removed=total_duplicates_removed,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in SSC Steno Custom generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINT: Generate Default SSC Steno (200 Qs)
# ============================================
@router.post("/ssc-steno/generate")
async def generate_ssc_steno(
    difficulty: str = Form("moderate"),
    previous_csvs: List[UploadFile] = File(default=[]),
):
    """Generate SSC Stenographer 2026 exam with exact syllabus breakdown (200 questions)."""
    all_mcqs = []
    breakdown = {}
    total_duplicates_removed = 0

    existing_questions = []
    if previous_csvs:
        csv_bytes = []
        for f in previous_csvs:
            if f.filename:
                raw = await f.read()
                if raw:
                    csv_bytes.append(raw)
        if csv_bytes:
            existing_questions = _parse_existing_csvs(csv_bytes)
            print(f"📂 Loaded {len(existing_questions)} existing questions from {len(csv_bytes)} CSV(s)")

    try:
        print(f"\n{'='*60}")
        print(f"  SSC STENO 2026 GENERATION")
        print(f"  Difficulty: {difficulty.upper()}  |  Target: {TOTAL_QUESTIONS}")
        print(f"{'='*60}")

        # PASS 1: Batch generate per subject
        for subject, details in SSC_STENO_SYLLABUS.items():
            print(f"\n📚 [{subject}] → {details['count']} questions | Part: {details['part']}")
            subject_mcqs = _generate_subject_batch(subject, details, difficulty)
            all_mcqs.extend(subject_mcqs)
            breakdown[subject] = len(subject_mcqs)

            if len(subject_mcqs) < details['count']:
                print(f"  ⚠️ Short by {details['count'] - len(subject_mcqs)}")

        print(f"\n{'─'*40}")
        print(f"After Pass 1: {len(all_mcqs)} / {TOTAL_QUESTIONS}")
        print(f"{'─'*40}")

        # PASS 2: Retry for short subjects
        for subject, details in SSC_STENO_SYLLABUS.items():
            current = breakdown.get(subject, 0)
            needed = details['count'] - current
            if needed <= 0:
                continue

            print(f"\n🔄 Retry [{subject}] → need {needed} more...", end=" ")
            qt = details['breakdown'][0]['type']
            retry_mcqs = _generate_for_type(subject, qt, needed, difficulty, max_attempts=2)

            if retry_mcqs:
                all_mcqs.extend(retry_mcqs)
                breakdown[subject] = breakdown.get(subject, 0) + len(retry_mcqs)
                print(f"✅ Got {len(retry_mcqs)}")
            else:
                print(f"❌ Failed")

        # DEDUP
        if existing_questions:
            print(f"\n{'─'*40}")
            print(f"🔍 Deduplicating against {len(existing_questions)} existing questions...")
            print(f"{'─'*40}")
            all_mcqs, total_duplicates_removed = _dedup_against_existing(all_mcqs, existing_questions)
            print(f"  Removed {total_duplicates_removed} duplicates. Remaining: {len(all_mcqs)}")

            breakdown = {}
            for m in all_mcqs:
                subj = m.get("Subject", "Unknown")
                breakdown[subj] = breakdown.get(subj, 0) + 1

        # PASS 3: Top-up
        top_up_round = 0
        max_top_up_rounds = 8
        while len(all_mcqs) < TOTAL_QUESTIONS and top_up_round < max_top_up_rounds:
            needed = TOTAL_QUESTIONS - len(all_mcqs)
            print(f"\n🔄 Top-up round {top_up_round+1}: need {needed} more questions...")

            shortfalls = []
            for subj, details in SSC_STENO_SYLLABUS.items():
                current = breakdown.get(subj, 0)
                target = details['count']
                gap = target - current
                if gap > 0:
                    shortfalls.append((subj, details, gap))
            shortfalls.sort(key=lambda x: -x[2])

            if not shortfalls:
                for subj, details in SSC_STENO_SYLLABUS.items():
                    shortfalls.append((subj, details, 1))
                random.shuffle(shortfalls)

            new_batch = []
            for subj, details, gap in shortfalls:
                if len(all_mcqs) + len(new_batch) >= TOTAL_QUESTIONS:
                    break
                gen_count = min(gap, TOTAL_QUESTIONS - len(all_mcqs) - len(new_batch))
                if gen_count <= 0:
                    continue

                type_idx = top_up_round % len(details['breakdown'])
                qt = details['breakdown'][type_idx]['type']

                print(f"  📝 [{subj}] generating {gen_count} ({qt})...", end=" ")
                fill_mcqs = _generate_for_type(subj, qt, gen_count + 1, difficulty, max_attempts=2)
                if fill_mcqs:
                    new_batch.extend(fill_mcqs[:gen_count])
                    print(f"✅ {min(len(fill_mcqs), gen_count)}")
                else:
                    print(f"❌")

            if existing_questions and new_batch:
                new_batch, batch_dupes = _dedup_against_existing(new_batch, existing_questions)
                total_duplicates_removed += batch_dupes

            all_mcqs.extend(new_batch)
            for m in new_batch:
                subj = m.get("Subject", "Unknown")
                breakdown[subj] = breakdown.get(subj, 0) + 1

            top_up_round += 1

        if not all_mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate any questions")

        if len(all_mcqs) > TOTAL_QUESTIONS:
            all_mcqs = all_mcqs[:TOTAL_QUESTIONS]

        # FINAL REPORT
        print(f"\n{'='*60}")
        print(f"  FINAL REPORT")
        print(f"{'='*60}")
        for subject, details in SSC_STENO_SYLLABUS.items():
            actual = breakdown.get(subject, 0)
            expected = details['count']
            status = "✅" if actual >= expected else f"⚠️ (short by {expected - actual})"
            print(f"  {subject:40s} {actual:3d}/{expected:3d}  {status}")
        print(f"{'─'*60}")
        print(f"  {'TOTAL':40s} {len(all_mcqs):3d}/{TOTAL_QUESTIONS}")
        if total_duplicates_removed:
            print(f"  {'DUPLICATES REMOVED':40s} {total_duplicates_removed}")
        print(f"{'='*60}")

        def format_to_row(m_dict):
            return {
                "Subject": m_dict.get('Subject', ''),
                "Topic": m_dict.get('Question_Type', ''),
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

        filename_base = f"ssc_steno_2026_{difficulty}_{uuid.uuid4().hex[:8]}"
        write_csv(filename_base, df)
        csv_url = f"/exports/{filename_base}.csv"

        return SSCStenoResponse(
            total_generated=len(all_mcqs),
            final_count=len(all_mcqs),
            csv_url=csv_url,
            breakdown=breakdown,
            duplicates_removed=total_duplicates_removed
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in SSC Steno generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
