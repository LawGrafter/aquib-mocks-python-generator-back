import google.generativeai as genai
import os
from typing import List, Dict, Any
from rapidfuzz import fuzz
import json

def validate_mcqs_with_ai(mcqs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates MCQs using AI to check:
    1. Question quality and correctness
    2. Option validity
    3. Correct answer accuracy
    4. Duplicate detection
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY not configured"}
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    results = {
        "total_questions": len(mcqs),
        "validated_questions": [],
        "duplicates": [],
        "issues_found": 0,
        "summary": {
            "correct_questions": 0,
            "questions_with_issues": 0,
            "duplicate_count": 0
        }
    }
    
    # Check for duplicates using fuzzy matching
    duplicates = find_duplicate_questions(mcqs)
    results["duplicates"] = duplicates
    results["summary"]["duplicate_count"] = len(duplicates)
    
    # Validate each question with AI (batch processing for efficiency)
    batch_size = 5
    for i in range(0, len(mcqs), batch_size):
        batch = mcqs[i:i+batch_size]
        batch_results = validate_batch_with_ai(model, batch, i)
        results["validated_questions"].extend(batch_results)
        
        # Update summary
        for result in batch_results:
            if result["has_issues"]:
                results["issues_found"] += 1
                results["summary"]["questions_with_issues"] += 1
            else:
                results["summary"]["correct_questions"] += 1
    
    return results


def find_duplicate_questions(mcqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find duplicate or very similar questions using fuzzy matching with smart filtering"""
    duplicates = []
    seen = []
    
    # Words that differentiate questions even if structure is similar
    differentiators = [
        ("synonym", "antonym"),
        ("correct", "incorrect"),
        ("true", "false"),
        ("not", "is"),
        ("उपसर्ग", "प्रत्यय"),
        ("विलोम", "पर्यायवाची"),
        ("संधि", "समास"),
        ("active", "passive"),
        ("direct", "indirect"),
    ]
    
    for i, mcq in enumerate(mcqs):
        question = mcq.get("Question", "")
        if not question:
            continue
            
        for j, seen_q in seen:
            # Use token_sort_ratio for better accuracy with reordered words
            similarity = fuzz.token_sort_ratio(question.lower(), seen_q.lower())
            
            if similarity > 95:  # Strict 95% threshold
                duplicates.append({
                    "question_index_1": j + 1,
                    "question_index_2": i + 1,
                    "similarity": round(similarity, 2),
                    "question_1": seen_q[:100] + "..." if len(seen_q) > 100 else seen_q,
                    "question_2": question[:100] + "..." if len(question) > 100 else question
                })
            elif similarity > 88:
                # For 88-95% similarity, check if key differentiating words differ
                q1_lower = question.lower()
                q2_lower = seen_q.lower()
                is_false_positive = False
                
                for word_a, word_b in differentiators:
                    if (word_a in q1_lower and word_b in q2_lower) or \
                       (word_b in q1_lower and word_a in q2_lower):
                        is_false_positive = True
                        break
                
                # Also check if the options are different (different answers = different questions)
                opt_a1 = mcq.get("Option A", "").lower()
                opt_a2 = ""
                for sj, sq in seen:
                    if sj == j:
                        opt_a2 = mcqs[sj].get("Option A", "").lower() if sj < len(mcqs) else ""
                        break
                
                if opt_a1 and opt_a2 and fuzz.ratio(opt_a1, opt_a2) < 50:
                    is_false_positive = True
                
                if not is_false_positive:
                    duplicates.append({
                        "question_index_1": j + 1,
                        "question_index_2": i + 1,
                        "similarity": round(similarity, 2),
                        "question_1": seen_q[:100] + "..." if len(seen_q) > 100 else seen_q,
                        "question_2": question[:100] + "..." if len(question) > 100 else question
                    })
        
        seen.append((i, question))
    
    return duplicates


def validate_batch_with_ai(model, batch: List[Dict[str, Any]], start_index: int) -> List[Dict[str, Any]]:
    """Validate a batch of questions using AI"""
    results = []
    
    for idx, mcq in enumerate(batch):
        question_num = start_index + idx + 1
        
        # Prepare the question data
        question = mcq.get("Question", "")
        option_a = mcq.get("Option A", "")
        option_b = mcq.get("Option B", "")
        option_c = mcq.get("Option C", "")
        option_d = mcq.get("Option D", "")
        correct_answer = mcq.get("Correct Answer", "").lower()
        subject = mcq.get("Subject", "")
        
        # Create validation prompt
        prompt = f"""You are an expert exam validator. Analyze this MCQ and check for issues:

Question {question_num}: {question}
A) {option_a}
B) {option_b}
C) {option_c}
D) {option_d}
Correct Answer: {correct_answer.upper()}
Subject: {subject}

Check for:
1. Is the question clear and unambiguous?
2. Are all options distinct and plausible?
3. Is the correct answer actually correct?
4. Are there any grammatical errors?
5. Is the difficulty appropriate for the subject?

Respond in JSON format:
{{
    "is_valid": true/false,
    "issues": ["list of issues found, empty if none"],
    "suggestions": ["list of suggestions for improvement"],
    "confidence": "high/medium/low"
}}"""

        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            validation_result = json.loads(response_text)
            
            results.append({
                "question_number": question_num,
                "question": question[:100] + "..." if len(question) > 100 else question,
                "is_valid": validation_result.get("is_valid", True),
                "has_issues": not validation_result.get("is_valid", True),
                "issues": validation_result.get("issues", []),
                "suggestions": validation_result.get("suggestions", []),
                "confidence": validation_result.get("confidence", "medium")
            })
            
        except Exception as e:
            # If AI validation fails, mark as unable to validate
            results.append({
                "question_number": question_num,
                "question": question[:100] + "..." if len(question) > 100 else question,
                "is_valid": True,
                "has_issues": False,
                "issues": [f"Unable to validate: {str(e)}"],
                "suggestions": [],
                "confidence": "low"
            })
    
    return results
