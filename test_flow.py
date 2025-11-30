"""
Test Flow Script for Consent & Privacy Service
Run this to verify all features are working
"""
import requests
import json
import uuid
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_KEY = "local-dev-key"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

def print_step(step_num: int, description: str):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*60}")

def print_response(response: requests.Response, show_body: bool = True):
    print(f"Status: {response.status_code}")
    if show_body and response.text:
        try:
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"Response: {response.text}")
    if response.status_code >= 400:
        print(f"⚠️  Error: {response.text[:500]}")

# Step 1: Check Health
print_step(1, "Health Check")
response = requests.get(f"{BASE_URL}/health")
print_response(response)
assert response.status_code == 200, "Service is not healthy!"

# Step 2: Detect Region
print_step(2, "Region Detection")
response = requests.get(f"{BASE_URL}/region")
print_response(response)
region_data = response.json()
detected_region = region_data.get("region", "ROW")
print(f"Detected Region: {detected_region}")

# Step 3: Create a User
print_step(3, "Create User")
user_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
user_data = {
    "email": user_email,
    "region": "EU"  # GDPR region for testing
}
response = requests.post(f"{BASE_URL}/users", headers=HEADERS, json=user_data)
print_response(response)
if response.status_code != 201:
    print(f"❌ Failed to create user. Status: {response.status_code}")
    print("This might be a database connection issue. Check your DATABASE_URL.")
    exit(1)
user_id = response.json()["id"]
print(f"✅ User Created: {user_id}")

# Step 4: Get User
print_step(4, "Get User Details")
response = requests.get(f"{BASE_URL}/users/{user_id}", headers=HEADERS)
print_response(response)
assert response.status_code == 200, "Failed to get user!"

# Step 5: Grant Consent (Analytics)
print_step(5, "Grant Consent for Analytics")
consent_data = {
    "user_id": user_id,
    "purpose": "analytics",
    "region": "EU"
}
response = requests.post(f"{BASE_URL}/consent/grant", headers=HEADERS, json=consent_data)
print_response(response)
assert response.status_code == 200, "Failed to grant consent!"
print("✅ Consent granted for analytics")

# Step 6: Check Decision (Should be ALLOWED for EU with explicit grant)
print_step(6, "Check Decision - Analytics (EU with grant)")
response = requests.get(
    f"{BASE_URL}/decision?user_id={user_id}&purpose=analytics",
    headers=HEADERS
)
print_response(response)
decision = response.json()
assert decision["allowed"] == True, "Decision should be ALLOWED!"
print(f"✅ Decision: ALLOWED - {decision['reason']}")

# Step 7: Check Decision (Should be DENIED for EU without grant)
print_step(7, "Check Decision - Ads (EU without grant)")
response = requests.get(
    f"{BASE_URL}/decision?user_id={user_id}&purpose=ads",
    headers=HEADERS
)
print_response(response)
decision = response.json()
assert decision["allowed"] == False, "Decision should be DENIED!"
print(f"✅ Decision: DENIED - {decision['reason']}")

# Step 8: Process Event (Analytics - Should be ALLOWED)
print_step(8, "Process Event - Page View (Analytics)")
event_data = {
    "user_id": user_id,
    "event_name": "page_view",
    "properties": {"path": "/home", "timestamp": "2024-01-01T00:00:00Z"}
}
response = requests.post(f"{BASE_URL}/events", headers=HEADERS, json=event_data)
print_response(response)
assert response.status_code == 200, "Failed to process event!"
event_result = response.json()
assert event_result["accepted"] == True, "Event should be accepted!"
print(f"✅ Event processed: {event_result['reason']}")

# Step 9: Process Event (Ads - Should be BLOCKED)
print_step(9, "Process Event - Ad Click (Ads - Should be blocked)")
event_data = {
    "user_id": user_id,
    "event_name": "ad_click",
    "properties": {"ad_id": "123", "campaign": "test"}
}
response = requests.post(f"{BASE_URL}/events", headers=HEADERS, json=event_data)
print_response(response)
event_result = response.json()
assert event_result["accepted"] == False, "Event should be blocked!"
print(f"✅ Event blocked: {event_result['reason']}")

# Step 10: Get Consent History
print_step(10, "Get Consent History")
response = requests.get(f"{BASE_URL}/consent/history/{user_id}", headers=HEADERS)
print_response(response)
assert response.status_code == 200, "Failed to get consent history!"
history = response.json()
print(f"✅ Found {len(history)} consent records")

# Step 11: Get Preferences
print_step(11, "Get User Preferences")
response = requests.get(f"{BASE_URL}/consent/preferences/{user_id}", headers=HEADERS)
print_response(response)
assert response.status_code == 200, "Failed to get preferences!"
prefs = response.json()
print(f"✅ Preferences retrieved for region: {prefs['region']}")

# Step 12: Create Export Request
print_step(12, "Create Export Request (Subject Rights)")
export_data = {
    "user_id": user_id,
    "request_type": "export"
}
response = requests.post(f"{BASE_URL}/subject-requests", headers=HEADERS, json=export_data)
print_response(response)
assert response.status_code == 201, "Failed to create export request!"
export_request = response.json()
request_id = export_request["request_id"]
token = export_request["verification_token"]
print(f"✅ Export request created: {request_id}")

# Step 13: Process Export Request
print_step(13, "Process Export Request")
response = requests.get(
    f"{BASE_URL}/subject-requests/{request_id}?token={token}",
    headers=HEADERS
)
print_response(response)
assert response.status_code == 200, "Failed to process export request!"
export_data = response.json()
print(f"✅ Export data retrieved: {len(export_data.get('history', []))} history records")

# Step 14: Revoke Consent
print_step(14, "Revoke Consent for Analytics")
revoke_data = {
    "user_id": user_id,
    "purpose": "analytics",
    "region": "EU"
}
response = requests.post(f"{BASE_URL}/consent/revoke", headers=HEADERS, json=revoke_data)
print_response(response)
assert response.status_code == 200, "Failed to revoke consent!"
print("✅ Consent revoked")

# Step 15: Check Decision After Revoke (Should be DENIED)
print_step(15, "Check Decision After Revoke")
response = requests.get(
    f"{BASE_URL}/decision?user_id={user_id}&purpose=analytics",
    headers=HEADERS
)
print_response(response)
decision = response.json()
assert decision["allowed"] == False, "Decision should be DENIED after revoke!"
print(f"✅ Decision: DENIED - {decision['reason']}")

# Step 16: Test US Region (CCPA - Default Allow)
print_step(16, "Test US Region (CCPA - Default Allow)")
us_user_data = {
    "email": f"us-test-{uuid.uuid4().hex[:8]}@example.com",
    "region": "US"
}
response = requests.post(f"{BASE_URL}/users", headers=HEADERS, json=us_user_data)
us_user_id = response.json()["id"]
print(f"✅ US User Created: {us_user_id}")

# Check decision without explicit consent (should be ALLOWED for US)
response = requests.get(
    f"{BASE_URL}/decision?user_id={us_user_id}&purpose=analytics",
    headers=HEADERS
)
decision = response.json()
assert decision["allowed"] == True, "US should default to ALLOW!"
print(f"✅ US Decision: ALLOWED - {decision['reason']} (CCPA default)")

# Step 17: Admin - View Users
print_step(17, "Admin - View Users")
response = requests.get(f"{BASE_URL}/admin/users", headers=HEADERS)
print_response(response, show_body=False)
assert response.status_code == 200, "Failed to get admin users!"
users = response.json()
print(f"✅ Found {len(users)} users in admin panel")

# Step 18: Admin - View Audit Logs
print_step(18, "Admin - View Audit Logs")
response = requests.get(f"{BASE_URL}/admin/audit", headers=HEADERS)
print_response(response, show_body=False)
assert response.status_code == 200, "Failed to get audit logs!"
audit_logs = response.json()
print(f"✅ Found {len(audit_logs)} audit log entries")

# Step 19: Admin - View Subject Requests
print_step(19, "Admin - View Subject Requests")
response = requests.get(f"{BASE_URL}/admin/subject-requests", headers=HEADERS)
print_response(response, show_body=False)
assert response.status_code == 200, "Failed to get subject requests!"
requests_list = response.json()
print(f"✅ Found {len(requests_list)} subject requests")

print(f"\n{'='*60}")
print("✅ ALL TESTS PASSED! Service is working correctly.")
print(f"{'='*60}")
print("\nSummary:")
print(f"  - User created: {user_id}")
print(f"  - Consent granted and revoked")
print(f"  - Decisions working (GDPR deny-by-default, CCPA allow-by-default)")
print(f"  - Events processed and blocked correctly")
print(f"  - Subject rights (export) working")
print(f"  - Admin endpoints accessible")
print(f"  - Audit logging functional")
print(f"\n🎉 Service is fully operational!")

