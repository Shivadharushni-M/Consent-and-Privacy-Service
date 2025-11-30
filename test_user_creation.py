#!/usr/bin/env python3

import requests
import uuid

def test_user_creation():
    """Test user creation endpoint."""
    # Generate unique email to avoid duplicates
    email = f'test-{uuid.uuid4().hex[:8]}@example.com'

    # Make API request
    response = requests.post(
        'http://localhost:8000/users',
        json={'email': email},
        headers={'X-API-Key': 'some-key-here'}
    )

    print(f'Status Code: {response.status_code}')

    if response.status_code == 201:
        print('✅ User created successfully!')
        data = response.json()
        print(f'User ID: {data["id"]}')
        print(f'Email: {data["email"]}')
        print(f'Region: {data["region"]}')
        return True
    else:
        print('❌ Error:', response.text)
        return False

if __name__ == '__main__':
    test_user_creation()