import requests
import os
from app.config import settings

print(f"API_KEY from settings: {settings.API_KEY}")
print(f"Current working directory: {os.getcwd()}")

# Test health endpoint
url = "http://localhost:8000/health"
headers = {
    "X-API-Key": settings.API_KEY,
    "Content-Type": "application/json"
}

print(f"Testing with API key: {settings.API_KEY}")

try:
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
