#!/usr/bin/env python3

import requests
import uuid
import time

BASE_URL = 'http://localhost:8000'
API_KEY = 'some-key-here'
HEADERS = {'X-API-Key': API_KEY}

def test_create_user():
    """Test POST /users - Create User"""
    print("\n🔹 Testing POST /users (Create User)")

    email = f'test-{uuid.uuid4().hex[:8]}@example.com'

    # Test with email only (region auto-detect)
    response = requests.post(
        f'{BASE_URL}/users',
        json={'email': email},
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print("✅ User created successfully!")
        print(f"User ID: {data['id']}")
        print(f"Email: {data['email']}")
        print(f"Region: {data['region']}")
        return data['id']
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_create_user_with_region():
    """Test POST /users with explicit region"""
    print("\n🔹 Testing POST /users with explicit region")

    email = f'test-{uuid.uuid4().hex[:8]}@example.com'

    response = requests.post(
        f'{BASE_URL}/users',
        json={'email': email, 'region': 'US'},
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print("✅ User created with US region!")
        print(f"User ID: {data['id']}")
        print(f"Email: {data['email']}")
        print(f"Region: {data['region']}")
        return data['id']
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_get_user(user_id):
    """Test GET /users/{user_id}"""
    print(f"\n🔹 Testing GET /users/{user_id}")

    response = requests.get(
        f'{BASE_URL}/users/{user_id}',
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ User retrieved successfully!")
        print(f"User ID: {data['id']}")
        print(f"Email: {data['email']}")
        print(f"Region: {data['region']}")
        print(f"Created At: {data['created_at']}")
        print(f"Updated At: {data['updated_at']}")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_update_user_region(user_id):
    """Test PATCH /users/{user_id}"""
    print(f"\n🔹 Testing PATCH /users/{user_id} (Update Region)")

    # First get current user data to compare timestamps
    response = requests.get(f'{BASE_URL}/users/{user_id}', headers=HEADERS)
    if response.status_code != 200:
        print("❌ Could not get user data for comparison")
        return False

    original_data = response.json()
    original_updated_at = original_data['updated_at']

    # Wait a moment to ensure timestamp difference
    time.sleep(1)

    # Update region
    response = requests.patch(
        f'{BASE_URL}/users/{user_id}',
        json={'region': 'EU'},
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ User region updated successfully!")
        print(f"User ID: {data['id']}")
        print(f"Email: {data['email']}")
        print(f"New Region: {data['region']}")

        # Check if updated_at changed
        if data['updated_at'] != original_updated_at:
            print("✅ updated_at timestamp was updated!")
        else:
            print("❌ updated_at timestamp was NOT updated")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_duplicate_email():
    """Test duplicate email returns 409"""
    print("\n🔹 Testing Duplicate Email (should return 409)")

    # Create first user
    email = f'test-{uuid.uuid4().hex[:8]}@example.com'
    response1 = requests.post(
        f'{BASE_URL}/users',
        json={'email': email},
        headers=HEADERS
    )

    if response1.status_code != 201:
        print("❌ Could not create first user for duplicate test")
        return False

    # Try to create second user with same email
    response2 = requests.post(
        f'{BASE_URL}/users',
        json={'email': email},
        headers=HEADERS
    )

    print(f"Status Code: {response2.status_code}")
    if response2.status_code == 409:
        print("✅ Duplicate email correctly returned 409!")
        return True
    else:
        print(f"❌ Expected 409, got {response2.status_code}: {response2.text}")
        return False

def test_invalid_region():
    """Test invalid region returns 422"""
    print("\n🔹 Testing Invalid Region (should return 422)")

    email = f'test-{uuid.uuid4().hex[:8]}@example.com'

    response = requests.post(
        f'{BASE_URL}/users',
        json={'email': email, 'region': 'INVALID_REGION'},
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 422:
        print("✅ Invalid region correctly returned 422!")
        return True
    else:
        print(f"❌ Expected 422, got {response.status_code}: {response.text}")
        return False

def test_missing_api_key():
    """Test missing API key returns 401"""
    print("\n🔹 Testing Missing API Key (should return 401)")

    email = f'test-{uuid.uuid4().hex[:8]}@example.com'

    response = requests.post(
        f'{BASE_URL}/users',
        json={'email': email}
        # No API key header
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 401:
        print("✅ Missing API key correctly returned 401!")
        return True
    else:
        print(f"❌ Expected 401, got {response.status_code}: {response.text}")
        return False

def test_get_nonexistent_user():
    """Test GET with nonexistent user ID"""
    print("\n🔹 Testing GET with nonexistent user ID (should return 404)")

    fake_user_id = str(uuid.uuid4())

    response = requests.get(
        f'{BASE_URL}/users/{fake_user_id}',
        headers=HEADERS
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 404:
        print("✅ Nonexistent user correctly returned 404!")
        return True
    else:
        print(f"❌ Expected 404, got {response.status_code}: {response.text}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing User Endpoints\n")

    results = []

    # Test user creation
    user_id = test_create_user()
    results.append(("Create User", user_id is not None))

    user_id2 = test_create_user_with_region()
    results.append(("Create User with Region", user_id2 is not None))

    # Test get user if we have a valid user ID
    if user_id:
        results.append(("Get User", test_get_user(user_id)))

    # Test update user region if we have a valid user ID
    if user_id:
        results.append(("Update User Region", test_update_user_region(user_id)))

    # Test error cases
    results.append(("Duplicate Email", test_duplicate_email()))
    results.append(("Invalid Region", test_invalid_region()))
    results.append(("Missing API Key", test_missing_api_key()))
    results.append(("Nonexistent User", test_get_nonexistent_user()))

    # Summary
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False

if __name__ == '__main__':
    main()