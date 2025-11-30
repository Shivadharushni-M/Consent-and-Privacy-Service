#!/usr/bin/env python3

import requests

def test_region_endpoint():
    """Test GET /region endpoint"""
    print("🔹 Testing GET /region endpoint")

    response = requests.get('http://localhost:8000/region')

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Region detection working!")
        print(f"Detected Region: {data['region']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

if __name__ == '__main__':
    test_region_endpoint()
