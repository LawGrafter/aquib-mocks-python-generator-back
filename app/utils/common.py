import re
import json
from typing import Dict, Any

def safe_json_parse(text: str) -> Dict[str, Any]:
    """
    Safely parses JSON from LLM response, handling markdown code blocks and common formatting issues.
    """
    if not text:
        return {}
        
    # Remove markdown code blocks if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Strip whitespace
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find the first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
                
        # If list
        start = text.find('[')
        end = text.rfind(']')
        
        if start != -1 and end != -1:
            try:
                return {"array": json.loads(text[start:end+1])}
            except json.JSONDecodeError:
                pass

        print(f"Failed to parse JSON. Raw text preview: {text[:200]}...")
        return {}
