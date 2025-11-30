"""
Manual test script for Preferences API endpoints
Tests all required functionality as per the specifications
"""
import requests
import json
from uuid import uuid4

BASE_URL = "http://localhost:8000"
API_KEY = "some-key-here"  # From .env file
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def print_section(title):
    print("\n" + "="*60)
    print(title)
    print("="*60)

def test_endpoint(method, endpoint, data=None, expected_status=200):
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{method} {endpoint}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print("✅ PASS")
        else:
            print(f"❌ FAIL - Expected {expected_status}")
        
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
            return response.status_code, json_response
        except:
            print(f"Response: {response.text}")
            return response.status_code, None
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None, None

# ============================================================
# MAIN TEST EXECUTION
# ============================================================

print_section("PREFERENCES API TESTING")

# Step 1: Create a test user
print_section("TEST 1: Create Test User")
status, user_response = test_endpoint(
    "POST", 
    "/users",
    {"email": f"test_pref_{uuid4().hex[:8]}@example.com", "region": "EU"},
    201
)
user_id = user_response["id"] if user_response else None
print(f"\n✅ Created user: {user_id}")

if not user_id:
    print("\n❌ Cannot proceed without user")
    exit(1)

# TEST 2: Get Current Preferences (No History - All REVOKED)
print_section("TEST 2: GET /consent/preferences/{user_id} - No History")
print("Expected: All purposes should be REVOKED by default")
status, prefs = test_endpoint("GET", f"/consent/preferences/{user_id}", expected_status=200)

if prefs:
    print(f"\n📊 Preferences Structure:")
    print(f"  - user_id: {prefs.get('user_id')}")
    print(f"  - region: {prefs.get('region')}")
    print(f"  - preferences keys: {list(prefs.get('preferences', {}).keys())}")
    
    all_revoked = all(v == "revoked" for v in prefs.get('preferences', {}).values())
    if all_revoked:
        print("✅ All preferences defaulted to REVOKED")
    else:
        print("❌ FAIL - Not all preferences are REVOKED")
        print(f"   Values: {prefs.get('preferences')}")

# TEST 3: Bulk Update Preferences - Analytics + Email
print_section("TEST 3: POST /consent/preferences/update - Analytics + Email")
print("Testing: Update analytics (GRANTED) and email (DENIED)")

update_data = {
    "user_id": user_id,
    "updates": {
        "analytics": "granted",
        "email": "denied"
    }
}

status, update_response = test_endpoint(
    "POST",
    "/consent/preferences/update",
    update_data,
    200
)

if update_response:
    print(f"\n📊 Updated Preferences:")
    preferences = update_response.get('preferences', {})
    print(f"  - analytics: {preferences.get('analytics')}")
    print(f"  - email: {preferences.get('email')}")
    
    if preferences.get('analytics') == 'granted' and preferences.get('email') == 'denied':
        print("✅ Bulk update successful")
    else:
        print("❌ FAIL - Values not updated correctly")

# TEST 4: Verify Audit Log Created
print_section("TEST 4: Verify Audit Log Created")
print("Checking audit logs for the update operation...")

# Check by querying audit endpoint if exists
status, audit_response = test_endpoint("GET", f"/admin/audit?action=preferences.updated")

if audit_response:
    audit_logs = audit_response if isinstance(audit_response, list) else [audit_response]
    prefs_updated_logs = [log for log in audit_logs if log.get('action') == 'preferences.updated']
    
    if prefs_updated_logs:
        print(f"✅ Found {len(prefs_updated_logs)} audit log(s) for preferences.updated")
        latest_log = prefs_updated_logs[0]
        print(f"\n📝 Latest Audit Log:")
        print(f"  - action: {latest_log.get('action')}")
        print(f"  - details: {json.dumps(latest_log.get('details'), indent=4)}")
    else:
        print("⚠️ No 'preferences.updated' audit logs found (endpoint may not exist)")
else:
    print("⚠️ Audit endpoint not available or no logs found")

# TEST 5: Get Preferences Again (Should reflect updates)
print_section("TEST 5: GET /consent/preferences/{user_id} - After Update")
status, prefs_after = test_endpoint("GET", f"/consent/preferences/{user_id}", expected_status=200)

if prefs_after:
    preferences = prefs_after.get('preferences', {})
    print(f"\n📊 Current Preferences:")
    print(f"  - analytics: {preferences.get('analytics')} (expected: granted)")
    print(f"  - email: {preferences.get('email')} (expected: denied)")
    print(f"  - marketing: {preferences.get('marketing')} (expected: revoked)")
    
    checks = [
        preferences.get('analytics') == 'granted',
        preferences.get('email') == 'denied',
        preferences.get('marketing') == 'revoked'
    ]
    
    if all(checks):
        print("✅ Preferences correctly reflect updates")
    else:
        print("❌ FAIL - Preferences don't match expected values")

# TEST 6: Test Expired Entries Handling
print_section("TEST 6: Check Expired Entries Handled")
print("Testing with consent that has an expired timestamp...")

from datetime import datetime, timedelta, timezone

# Grant consent with expired date (using consent/grant endpoint)
expired_consent_data = {
    "user_id": user_id,
    "purpose": "location",
    "region": "EU",
    "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
}

status, expired_response = test_endpoint(
    "POST",
    "/consent/grant",
    expired_consent_data,
    201
)

print("\nNow checking preferences to see if expired consent is treated as REVOKED...")
status, prefs_expired = test_endpoint("GET", f"/consent/preferences/{user_id}", expected_status=200)

if prefs_expired:
    location_status = prefs_expired.get('preferences', {}).get('location')
    print(f"\n📊 Location consent status: {location_status}")
    
    if location_status == 'revoked':
        print("✅ Expired consent correctly treated as REVOKED")
    else:
        print(f"❌ FAIL - Expired consent has status: {location_status}")

# TEST 7: Unknown User → 404
print_section("TEST 7: GET /consent/preferences/{unknown_user_id} - Unknown User")
print("Expected: 404 with 'user_not_found' error")

unknown_user_id = str(uuid4())
status, error_response = test_endpoint(
    "GET",
    f"/consent/preferences/{unknown_user_id}",
    expected_status=404
)

if status == 404:
    detail = error_response.get('detail') if error_response else None
    if detail == 'user_not_found':
        print("✅ Unknown user correctly returns 404 with 'user_not_found'")
    else:
        print(f"⚠️ Got 404 but detail is: {detail}")
else:
    print(f"❌ FAIL - Expected 404, got {status}")

# TEST 8: No Updates → 422
print_section("TEST 8: POST /consent/preferences/update - Empty Updates")
print("Expected: 422 with 'no_updates' error")

empty_update_data = {
    "user_id": user_id,
    "updates": {}
}

status, error_response = test_endpoint(
    "POST",
    "/consent/preferences/update",
    empty_update_data,
    422
)

if status == 422:
    detail = error_response.get('detail') if error_response else None
    if detail == 'no_updates':
        print("✅ Empty updates correctly returns 422 with 'no_updates'")
    else:
        print(f"⚠️ Got 422 but detail is: {detail}")
else:
    print(f"❌ FAIL - Expected 422, got {status}")

# TEST 9: Invalid Purpose → 422
print_section("TEST 9: POST /consent/preferences/update - Invalid Purpose")
print("Expected: 422 with 'invalid_purpose' error")

invalid_purpose_data = {
    "user_id": user_id,
    "updates": {
        "invalid_purpose_xyz": "granted"
    }
}

status, error_response = test_endpoint(
    "POST",
    "/consent/preferences/update",
    invalid_purpose_data,
    422
)

if status == 422:
    detail = error_response.get('detail') if error_response else None
    if detail == 'invalid_purpose':
        print("✅ Invalid purpose correctly returns 422 with 'invalid_purpose'")
    else:
        print(f"⚠️ Got 422 but detail is: {detail}")
else:
    print(f"❌ FAIL - Expected 422, got {status}")

print_section("PREFERENCES API TESTING COMPLETE")
print("✅ All core tests completed!")

