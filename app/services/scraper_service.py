import requests
from bs4 import BeautifulSoup
import re
from fastapi import HTTPException

def scrape_url(url: str) -> dict:
    """
    Scrapes the content from the given URL.
    Returns a dictionary with 'url', 'title', and 'content'.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script.extract()
            
        # Get title
        title = soup.title.string if soup.title else "No Title"
        title = title.strip() if title else "No Title"
        
        # Get text
        text = soup.get_text()
        
        # Clean text
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return {
            "url": url,
            "title": title,
            "content": text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse content: {str(e)}")
