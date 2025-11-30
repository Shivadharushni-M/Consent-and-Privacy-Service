#!/usr/bin/env python3
"""Test the Consent and Privacy Service"""
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"
API_KEY = "local-dev-key"  # From config.py default

headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def test_endpoint(method, endpoint, data=None, description=""):
    """Test an endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {description or endpoint}")
    print(f"{method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        else:
            print(f"Unsupported method: {method}")
            return None
            
        print(f"Status: {response.status_code}")
        if response.status_code < 400:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"Error: {response.text}")
        return response
    except Exception as e:
        print(f"Exception: {e}")
        return None

# Test basic endpoints
print("="*60)
print("CONSENT AND PRIVACY SERVICE - COMPREHENSIVE TEST")
print("="*60)

# 1. Root endpoint (no auth required)
test_endpoint("GET", "/", description="Root endpoint")
test_endpoint("GET", "/health", description="Health check")

# 2. Create a user
user_data = {
    "email": f"test_{uuid4().hex[:8]}@example.com",
    "region": "EU"
}
user_response = test_endpoint("POST", "/users", user_data, "Create user")
if user_response and user_response.status_code == 201:
    user_id = user_response.json()["id"]
    print(f"\n✅ Created user with ID: {user_id}")
    
    # 3. Get user
    test_endpoint("GET", f"/users/{user_id}", description="Get user")
    
    # 4. Grant consent
    consent_data = {
        "user_id": user_id,
        "purpose": "analytics",
        "region": "EU"
    }
    test_endpoint("POST", "/consent/grant", consent_data, "Grant consent")
    
    # 5. Grant another consent
    consent_data2 = {
        "user_id": user_id,
        "purpose": "marketing",
        "region": "EU"
    }
    test_endpoint("POST", "/consent/grant", consent_data2, "Grant marketing consent")
    
    # 6. Get consent history
    test_endpoint("GET", f"/consent/history/{user_id}", description="Get consent history")
    
    # 7. Revoke consent
    test_endpoint("POST", "/consent/revoke", consent_data, "Revoke consent")
    
    # 8. Create subject request (export)
    subject_request_data = {
        "user_id": user_id,
        "request_type": "export"
    }
    request_response = test_endpoint("POST", "/subject-requests", subject_request_data, "Create export request")
    
    if request_response and request_response.status_code == 201:
        request_data = request_response.json()
        request_id = request_data["request_id"]
        token = request_data.get("verification_token", "")
        print(f"\n✅ Created export request: {request_id}")
        
        # 9. Process export request
        if token:
            test_endpoint("GET", f"/subject-requests/export/{request_id}?token={token}", 
                         description="Process export request")
    
    # 10. Create access request
    access_request_data = {
        "user_id": user_id,
        "request_type": "access"
    }
    access_response = test_endpoint("POST", "/subject-requests", access_request_data, "Create access request")
    
    if access_response and access_response.status_code == 201:
        access_data = access_response.json()
        access_id = access_data["request_id"]
        access_token = access_data.get("verification_token", "")
        if access_token:
            test_endpoint("GET", f"/subject-requests/access/{access_id}?token={access_token}",
                         description="Process access request")
    
    # 11. Test preferences
    test_endpoint("GET", f"/preferences/{user_id}", description="Get user preferences")
    
    # 12. Test region endpoint (no auth)
    test_endpoint("GET", "/region/detect", description="Detect region (no auth)")
    
    # 13. Test admin endpoints
    test_endpoint("GET", "/admin/users", description="List all users (admin)")
    test_endpoint("GET", "/admin/audit", description="Get audit logs (admin)")
    test_endpoint("GET", "/admin/subject-requests", description="List subject requests (admin)")
    
    # 14. Update user region
    update_data = {"region": "US"}
    test_endpoint("PATCH", f"/users/{user_id}", update_data, "Update user region")
    
else:
    print("\n❌ Failed to create user. Cannot continue with other tests.")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)

