#!/usr/bin/env python3
"""Test the Consent Management Core Features"""
import json
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.database import Base, get_db
from app.main import create_app
from app.models.consent import RegionEnum, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_consent.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def _create_user(email: str, region: RegionEnum = RegionEnum.EU) -> str:
    db = TestingSessionLocal()
    try:
        user = User(email=email, region=region)
        db.add(user)
        db.commit()
        db.refresh(user)
        return str(user.id)
    finally:
        db.close()

def test_endpoint(client, method, endpoint, data=None, description="", expected_status=200):
    """Test an endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {description or endpoint}")
    print(f"{method} {endpoint}")

    try:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json=data)
        else:
            print(f"Unsupported method: {method}")
            return None

        print(f"Status: {response.status_code}")
        if response.status_code == expected_status:
            print("✅ PASS")
            if response.status_code < 400:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response
        else:
            print(f"❌ FAIL - Expected {expected_status}, got {response.status_code}")
            print(f"Error: {response.text}")
            return response
    except Exception as e:
        print(f"Exception: {e}")
        return None

# Setup test client
Base.metadata.create_all(bind=engine)
app = create_app()
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app, headers={"X-API-Key": settings.API_KEY})

print("="*60)
print("CONSENT MANAGEMENT CORE FEATURES TEST")
print("="*60)

# 1. Create a user first
user_data = {
    "email": f"test_consent_{uuid4().hex[:8]}@example.com",
    "region": "EU"
}
user_response = test_endpoint(client, "POST", "/users", user_data, "Create user", 201)
if user_response and user_response.status_code == 201:
    user_id = user_response.json()["id"]
    print(f"\n✅ Created user with ID: {user_id}")

    # TEST 1: Grant Consent
    print("\n" + "="*60)
    print("TEST 1: GRANT CONSENT")
    print("="*60)

    consent_data = {
        "user_id": user_id,
        "purpose": "analytics",
        "region": "EU"
    }
    grant_response = test_endpoint(client, "POST", "/consent/grant", consent_data, "Grant consent for analytics", 201)

    if grant_response and grant_response.status_code == 201:
        grant_data = grant_response.json()
        print("✅ Grant consent works")
        print(f"   - Consent ID: {grant_data['id']}")
        print(f"   - Status: {grant_data['status']}")
        print(f"   - Purpose: {grant_data['purpose']}")
        print(f"   - Region: {grant_data['region']}")
        print(f"   - Policy snapshot: {grant_data['policy_snapshot']}")

    # TEST 2: Get Consent History (should show granted consent)
    print("\n" + "="*60)
    print("TEST 2: CONSENT HISTORY - After Grant")
    print("="*60)

    history_response = test_endpoint(client, "GET", f"/consent/history/{user_id}", description="Get consent history after grant", expected_status=200)

    if history_response and history_response.status_code == 200:
        history_data = history_response.json()
        print(f"✅ History returned {len(history_data)} records")
        if len(history_data) == 1:
            print("✅ Grant appears in history")
            print(f"   - Status: {history_data[0]['status']}")
            print(f"   - Purpose: {history_data[0]['purpose']}")
            print(f"   - Order: Newest first (timestamp desc)")
        else:
            print(f"❌ Expected 1 record, got {len(history_data)}")

    # TEST 3: Grant another consent
    print("\n" + "="*60)
    print("TEST 3: GRANT ADDITIONAL CONSENT")
    print("="*60)

    consent_data2 = {
        "user_id": user_id,
        "purpose": "marketing",
        "region": "EU"
    }
    grant_response2 = test_endpoint(client, "POST", "/consent/grant", consent_data2, "Grant consent for marketing", 201)

    # TEST 4: Revoke Consent
    print("\n" + "="*60)
    print("TEST 4: REVOKE CONSENT")
    print("="*60)

    revoke_response = test_endpoint(client, "POST", "/consent/revoke", consent_data, "Revoke analytics consent", 201)

    if revoke_response and revoke_response.status_code == 201:
        revoke_data = revoke_response.json()
        print("✅ Revoke consent works")
        print(f"   - Status: {revoke_data['status']}")
        print(f"   - Purpose: {revoke_data['purpose']}")

    # TEST 5: Get Consent History (should show revoke as new entry)
    print("\n" + "="*60)
    print("TEST 5: CONSENT HISTORY - After Revoke")
    print("="*60)

    history_response2 = test_endpoint(client, "GET", f"/consent/history/{user_id}", description="Get consent history after revoke", expected_status=200)

    if history_response2 and history_response2.status_code == 200:
        history_data2 = history_response2.json()
        print(f"✅ History returned {len(history_data2)} records")
        if len(history_data2) == 3:  # grant analytics, grant marketing, revoke analytics
            print("✅ All entries appear in history")
            print(f"   - Newest (index 0): {history_data2[0]['purpose']} - {history_data2[0]['status']}")
            print(f"   - Middle (index 1): {history_data2[1]['purpose']} - {history_data2[1]['status']}")
            print(f"   - Oldest (index 2): {history_data2[2]['purpose']} - {history_data2[2]['status']}")

            # Check order is newest first
            if history_data2[0]['timestamp'] >= history_data2[1]['timestamp'] >= history_data2[2]['timestamp']:
                print("✅ Order is newest first")
            else:
                print("❌ Order is NOT newest first")
        else:
            print(f"❌ Expected 3 records, got {len(history_data2)}")

    # TEST 6: Test Append-only behavior (no updates/deletes)
    print("\n" + "="*60)
    print("TEST 6: APPEND-ONLY BEHAVIOR")
    print("="*60)

    # Grant the same consent again (should create new entry, not update)
    grant_again_response = test_endpoint(client, "POST", "/consent/grant", consent_data, "Grant analytics consent again", 201)

    history_response3 = test_endpoint(client, "GET", f"/consent/history/{user_id}", description="Get consent history after duplicate grant", expected_status=200)

    if history_response3 and history_response3.status_code == 200:
        history_data3 = history_response3.json()
        analytics_records = [r for r in history_data3 if r['purpose'] == 'analytics']
        print(f"✅ Found {len(analytics_records)} analytics records")
        if len(analytics_records) == 3:  # grant, revoke, grant again
            print("✅ Append-only: New record created instead of updating existing")
        else:
            print(f"❌ Expected 3 analytics records, got {len(analytics_records)}")

    # TEST 7: Test Missing Purpose Validation
    print("\n" + "="*60)
    print("TEST 7: MISSING PURPOSE VALIDATION")
    print("="*60)

    invalid_consent_data = {
        "user_id": user_id,
        "purpose": "invalid_purpose",
        "region": "EU"
    }
    invalid_response = test_endpoint(client, "POST", "/consent/grant", invalid_consent_data, "Grant consent with invalid purpose", 422)

    if invalid_response and invalid_response.status_code == 422:
        print("✅ Invalid purpose correctly rejected with 422")
    else:
        print("❌ Invalid purpose should return 422")

    # TEST 8: Test Expiry Logic
    print("\n" + "="*60)
    print("TEST 8: EXPIRY LOGIC")
    print("="*60)

    from datetime import datetime, timedelta, timezone
    expired_expiry = datetime.now(timezone.utc) - timedelta(days=1)  # Already expired

    expired_consent_data = {
        "user_id": user_id,
        "purpose": "location",
        "region": "EU",
        "expires_at": expired_expiry.isoformat()
    }

    expired_response = test_endpoint(client, "POST", "/consent/grant", expired_consent_data, "Grant consent with expired date", 201)

    # Check preferences endpoint to see if expired consent is treated as revoked
    preferences_response = test_endpoint(client, "GET", f"/consent/preferences/{user_id}", description="Get user preferences to check expiry handling", expected_status=200)

    if preferences_response and preferences_response.status_code == 200:
        prefs_data = preferences_response.json()
        print(f"✅ Preferences response structure: {list(prefs_data.keys())}")
        location_status = prefs_data['preferences'].get('location', 'not_found')
        print(f"✅ Location consent status in preferences: {location_status}")
        if location_status == 'revoked':
            print("✅ Expired consent treated as revoked")
        else:
            print("❌ Expected expired consent to be treated as revoked, got:", location_status)

else:
    print("\n❌ Failed to create user. Cannot continue with consent tests.")

print("\n" + "="*60)
print("CONSENT MANAGEMENT TESTING COMPLETE")
print("="*60)
