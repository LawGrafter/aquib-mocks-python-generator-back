import requests
import os

BASE_URL = "http://127.0.0.1:8000"

def create_dummy_pdf(filename):
    # Create a minimal valid PDF
    content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000157 00000 n \n0000000302 00000 n \n0000000389 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n484\n%%EOF"
    with open(filename, "wb") as f:
        f.write(content)

def test_upload():
    filename = "test_dummy.pdf"
    create_dummy_pdf(filename)
    
    print(f"Uploading {filename}...")
    try:
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            resp = requests.post(f"{BASE_URL}/upload-pdf", files=files)
            
        if resp.status_code == 200:
            print("Success:", resp.json())
        else:
            print("Failed:", resp.status_code, resp.text)
            
    except Exception as e:
        print("Error:", e)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_upload()
