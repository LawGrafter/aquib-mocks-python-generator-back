import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    # 1. Upload PDF
    print("Uploading PDF...")
    files = {'file': open('test.pdf', 'rb')}
    resp = requests.post(f"{BASE_URL}/upload-pdf", files=files)
    if resp.status_code != 200:
        print("Upload failed:", resp.text)
        return
    
    data = resp.json()
    file_id = data['file_id']
    print(f"Upload success. File ID: {file_id}")

    # 2. Convert to TXT
    print("Converting to TXT...")
    payload_txt = {"file_id": file_id, "output_format": "txt"}
    resp_txt = requests.post(f"{BASE_URL}/convert-text", json=payload_txt)
    if resp_txt.status_code == 200:
        print("TXT Conversion success:", resp_txt.json())
        # Verify download link
        download_url = resp_txt.json()['download_url']
        file_resp = requests.get(f"{BASE_URL}{download_url}")
        if file_resp.status_code == 200:
             print("TXT Download verified.")
        else:
             print(f"TXT Download failed: {file_resp.status_code}")
    else:
        print("TXT Conversion failed:", resp_txt.text)

    # 3. Convert to DOCX
    print("Converting to DOCX...")
    payload_doc = {"file_id": file_id, "output_format": "doc"}
    resp_doc = requests.post(f"{BASE_URL}/convert-text", json=payload_doc)
    if resp_doc.status_code == 200:
        print("DOCX Conversion success:", resp_doc.json())
        # Verify download link
        download_url = resp_doc.json()['download_url']
        file_resp = requests.get(f"{BASE_URL}{download_url}")
        if file_resp.status_code == 200:
             print("DOCX Download verified.")
        else:
             print(f"DOCX Download failed: {file_resp.status_code}")
    else:
        print("DOCX Conversion failed:", resp_doc.text)

if __name__ == "__main__":
    test_flow()
