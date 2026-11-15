
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("QRAIL_API_KEY")

if not API_KEY:
    print("API key not found")
    raise SystemExit(1)

url = "https://api.qrail.in/api/v1/trains/pnr/status"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

params = {
    "train": 12393
}

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print("HTTP Status:", response.status_code)
    print("Response:")

    try:
        print(response.json())
    except ValueError:
        print(response.text[:1000])

except requests.RequestException as error:
    print("Connection error:", error)
