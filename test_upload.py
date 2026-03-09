import requests

url = "http://127.0.0.1:8000/upload-pdf"
files = {'file': open('test.pdf', 'rb')}

try:
    response = requests.post(url, files=files)
    print(response.status_code)
    print(response.json())
except Exception as e:
    print(e)
