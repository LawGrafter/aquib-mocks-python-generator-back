import requests
import uuid
import os
import time

BASE_URL = "http://127.0.0.1:8000"
STORAGE_TEXT = "app/storage/text"

def test_export_flow():
    # 1. Setup: Create a dummy text file
    file_id = str(uuid.uuid4())
    text_content = """
    The Amazon rainforest is the largest rainforest in the world.
    It covers much of northwestern Brazil and extending into Colombia, Peru and other South American countries.
    The Amazon River is the largest river by discharge volume of water in the world.
    """
    
    os.makedirs(STORAGE_TEXT, exist_ok=True)
    with open(os.path.join(STORAGE_TEXT, f"{file_id}.txt"), "w", encoding="utf-8") as f:
        f.write(text_content)
        
    print(f"1. Created text file: {file_id}")
    
    # 2. Generate MCQs
    mcq_payload = {
        "file_id": file_id,
        "total_questions": 2,
        "difficulty": "medium"
    }
    
    print("2. Generating MCQs...")
    resp = requests.post(f"{BASE_URL}/generate-mcq", json=mcq_payload)
    if resp.status_code != 200:
        print("Failed to generate MCQs:", resp.text)
        return
    print("   MCQs Generated successfully.")
    
    # 3. Export to CSV
    export_payload = {
        "file_id": file_id
    }
    
    print("3. Exporting to CSV...")
    resp = requests.post(f"{BASE_URL}/export-csv", json=export_payload)
    if resp.status_code != 200:
        print("Failed to export CSV:", resp.text)
        return
        
    data = resp.json()
    csv_url = data['csv_url']
    print(f"   Success! CSV URL: {csv_url}")
    
    # 4. Verify Download
    full_url = f"{BASE_URL}{csv_url}"
    print(f"4. Downloading CSV from {full_url}...")
    resp = requests.get(full_url)
    if resp.status_code == 200:
        content = resp.text
        print("\n--- CSV CONTENT START ---")
        print(content)
        print("--- CSV CONTENT END ---")
        
        # Simple validation
        if "Question,Option A" in content:
            print("\n✅ Verification Passed: CSV Header found.")
        else:
            print("\n❌ Verification Failed: CSV Header missing.")
    else:
        print(f"Failed to download CSV: {resp.status_code}")

if __name__ == "__main__":
    test_export_flow()
