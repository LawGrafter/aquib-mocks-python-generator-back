import re

def normalize_text(text: str) -> str:
    """
    Normalizes text by removing extra whitespace and fixing newlines.
    """
    if not text:
        return ""
    
    # Replace multiple newlines with a single newline (or keep max 2 for paragraph separation)
    # Strategy: Replace 3+ newlines with 2 newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Replace multiple spaces with single space, but preserve newlines
    # We can do this line by line or use a careful regex
    lines = text.split('\n')
    cleaned_lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
    
    return '\n'.join(cleaned_lines).strip()

def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """
    Splits text into chunks with overlap.
    """
    if not text:
        return []
        
    if len(text) <= max_chars:
        return [text]
        
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # If we are not at the end, try to break at a newline or space to avoid cutting words
        if end < len(text):
            # Look for the last newline in the range [end - overlap/2, end]
            # giving preference to paragraph breaks
            search_window = text[end - 100 : end] if end > 100 else text[:end]
            last_newline = search_window.rfind('\n')
            
            if last_newline != -1:
                # Adjust end to the newline position relative to start
                # Actually, search_window logic is a bit tricky with indices. 
                # Let's simplify: look backwards from 'end' for a space or newline.
                
                # Search backwards from 'end' up to 'overlap' distance
                boundary_found = False
                for i in range(end, max(start, end - 200), -1):
                    if text[i] in ['\n', ' ']:
                        end = i
                        boundary_found = True
                        break
                
                # If no natural break found, we just cut at max_chars (hard break)
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        start = end - overlap
        
        # Ensure we move forward
        if start >= len(text):
            break
            
    return chunks
