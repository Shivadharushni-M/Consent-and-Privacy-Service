import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"
API_KEY = "some-key-here"
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def test_simple():
    # Create a test user first
    print("Creating test user...")
    user_data = {"email": f"test_debug_{uuid4().hex[:8]}@example.com", "region": "EU"}
    response = requests.post(f"{BASE_URL}/users", headers=HEADERS, json=user_data)
    print(f"User creation: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 201:
        user_data = response.json()
        user_id = user_data["id"]
        print(f"User ID: {user_id}")

        # Test preferences update
        print("Testing preferences update...")
        update_data = {
            "user_id": user_id,
            "updates": {
                "analytics": "granted",
                "email": "denied"
            }
        }
        print(f"Sending update data: {json.dumps(update_data, indent=2)}")
        response = requests.post(f"{BASE_URL}/consent/preferences/update", headers=HEADERS, json=update_data)
        print(f"Preferences update: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code != 200:
            print("Headers sent:")
            for k, v in HEADERS.items():
                print(f"  {k}: {v}")

test_simple()
