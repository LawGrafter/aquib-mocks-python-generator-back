import requests
import uuid
import os

BASE_URL = "http://127.0.0.1:8000"
STORAGE_TEXT = "app/storage/text"

def test_mcq_generation():
    # 1. Simulate a stored text file
    file_id = str(uuid.uuid4())
    text_content = """
    Rash Behari Bose was a revolutionary leader who founded the Indian National Army.
    He was born in 1886 in the Subaldaha village of Bardhaman district.
    The Ghadar Mutiny was planned for February 1915 but failed due to treachery.
    Subhash Chandra Bose took over the leadership of INA in 1943 in Singapore.
    The Battle of Plassey was fought in 1757 between the British East India Company and the Nawab of Bengal.
    Mahatma Gandhi returned to India from South Africa in 1915.
    """
    
    # Ensure directory exists
    os.makedirs(STORAGE_TEXT, exist_ok=True)
    
    file_path = os.path.join(STORAGE_TEXT, f"{file_id}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_content)
        
    print(f"Created dummy text file: {file_id}")
    
    # 2. Call Generate MCQ API
    payload = {
        "file_id": file_id,
        "total_questions": 3,
        "difficulty": "medium"
    }
    
    print("Requesting MCQs...")
    try:
        resp = requests.post(f"{BASE_URL}/generate-mcq", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            mcqs = data['mcqs']
            print(f"Success! Generated {len(mcqs)} MCQs.")
            for i, item in enumerate(mcqs):
                print(f"\nQ{i+1}: {item['question']}")
                print(f"Options: {item['options']}")
                print(f"Answer: {item['correct_answer']}")
        else:
            print("Failed:", resp.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_mcq_generation()
