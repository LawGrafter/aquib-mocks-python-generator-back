import requests

BASE_URL = "http://127.0.0.1:8000"

def test_answer_key():
    print("Generating Answer Key...")
    payload = {"total_questions": 25}
    try:
        resp = requests.post(f"{BASE_URL}/generate-answer-key", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            key = data['answer_key']
            print(f"Success. Key: {key}")
            print(f"Length: {len(key)}")
            
            # Simple validation
            if len(key) == 25 and all(c in 'abcd' for c in key):
                 print("Validation Passed.")
            else:
                 print("Validation Failed.")
        else:
            print("Failed:", resp.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_answer_key()
