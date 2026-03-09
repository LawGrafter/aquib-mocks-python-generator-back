import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini():
    # 1. Load Environment Variables
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    print("--- Gemini API Verification ---")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment.")
        print("Please ensure you have a .env file with GEMINI_API_KEY=your_key")
        return
    
    if "your_gemini_api_key_here" in api_key:
        print("ERROR: GEMINI_API_KEY is still the placeholder.")
        print("Please edit .env and paste your actual API key.")
        return

    print(f"API Key loaded: {api_key[:5]}...{api_key[-5:]}")
    
    # 2. Configure Gemini
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        print("Sending test request to Gemini...")
        response = model.generate_content("Generate one multiple choice question about Python programming in JSON format.")
        
        print("\n--- Response Received ---")
        print(response.text)
        print("\nSUCCESS: Gemini API is working!")
        
    except Exception as e:
        print(f"\nERROR: API Call failed. Reason: {e}")

if __name__ == "__main__":
    test_gemini()
