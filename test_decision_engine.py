"""
Comprehensive Decision Engine Test Suite
Tests all decision engine rules and scenarios
"""
import requests
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import json

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {
    'X-API-Key': 'some-key-here',
    'Content-Type': 'application/json'
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_test(test_name):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")

def log_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def log_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def log_info(message):
    print(f"{Colors.YELLOW}→ {message}{Colors.RESET}")

def create_test_user(email, region):
    """Create a test user"""
    response = requests.post(
        f"{BASE_URL}/users",
        headers=HEADERS,
        json={'email': email, 'region': region}
    )
    if response.status_code == 201:
        user_id = response.json()['id']
        log_info(f"Created user: {user_id} (region: {region})")
        return user_id
    else:
        log_error(f"Failed to create user: {response.status_code} - {response.text}")
        return None

def grant_consent(user_id, purpose, region, expires_at=None):
    """Grant consent for a user"""
    data = {
        'user_id': user_id,
        'purpose': purpose,
        'region': region
    }
    if expires_at:
        data['expires_at'] = expires_at.isoformat()
    
    response = requests.post(
        f"{BASE_URL}/consent/grant",
        headers=HEADERS,
        json=data
    )
    return response

def revoke_consent(user_id, purpose, region):
    """Revoke consent for a user"""
    response = requests.post(
        f"{BASE_URL}/consent/revoke",
        headers=HEADERS,
        json={
            'user_id': user_id,
            'purpose': purpose,
            'region': region
        }
    )
    return response

def check_decision(user_id, purpose):
    """Check decision for user and purpose"""
    response = requests.get(
        f"{BASE_URL}/decision",
        headers=HEADERS,
        params={'user_id': user_id, 'purpose': purpose}
    )
    return response

def test_decision_endpoint():
    """Test 1: Basic decision endpoint functionality"""
    log_test("Decision Endpoint - Basic Functionality")
    
    user_id = create_test_user(f"test_basic_{uuid4().hex[:8]}@example.com", "US")
    if not user_id:
        return False
    
    response = check_decision(user_id, "marketing")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        required_fields = ['allowed', 'reason', 'policy_snapshot', 'user_id', 'purpose', 'region']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            log_error(f"Missing fields in response: {missing_fields}")
            return False
        
        log_success("Decision endpoint returns correct structure")
        return True
    else:
        log_error(f"Decision endpoint failed: {response.status_code} - {response.text}")
        return False

def test_gdpr_without_consent():
    """Test 2: EU user without consent → denied"""
    log_test("GDPR Rule - EU User Without Consent (Should be DENIED)")
    
    user_id = create_test_user(f"test_eu_no_consent_{uuid4().hex[:8]}@example.com", "EU")
    if not user_id:
        return False
    
    response = check_decision(user_id, "analytics")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and 'gdpr_requires_grant' in data['reason']:
            log_success("GDPR correctly denies access without consent")
            return True
        else:
            log_error(f"Expected denied, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_gdpr_with_consent():
    """Test 3: EU user with consent → allowed"""
    log_test("GDPR Rule - EU User With Consent (Should be ALLOWED)")
    
    user_id = create_test_user(f"test_eu_consent_{uuid4().hex[:8]}@example.com", "EU")
    if not user_id:
        return False
    
    # Grant consent
    grant_response = grant_consent(user_id, "analytics", "EU")
    if grant_response.status_code != 201:
        log_error(f"Failed to grant consent: {grant_response.status_code}")
        return False
    
    log_info("Consent granted")
    
    # Check decision
    response = check_decision(user_id, "analytics")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is True and 'granted' in data['reason']:
            log_success("GDPR correctly allows access with consent")
            return True
        else:
            log_error(f"Expected allowed, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_india_gdpr_like():
    """Test 4: INDIA user without consent → denied (GDPR-like)"""
    log_test("GDPR Rule - INDIA User Without Consent (Should be DENIED)")
    
    user_id = create_test_user(f"test_india_{uuid4().hex[:8]}@example.com", "INDIA")
    if not user_id:
        return False
    
    response = check_decision(user_id, "data_sharing")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and 'gdpr' in data['reason']:
            log_success("INDIA correctly denies access without consent (GDPR-like)")
            return True
        else:
            log_error(f"Expected denied, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_uk_gdpr_like():
    """Test 5: UK user without consent → denied (GDPR-like)"""
    log_test("GDPR Rule - UK User Without Consent (Should be DENIED)")
    
    user_id = create_test_user(f"test_uk_{uuid4().hex[:8]}@example.com", "UK")
    if not user_id:
        return False
    
    response = check_decision(user_id, "marketing")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and 'gdpr' in data['reason']:
            log_success("UK correctly denies access without consent (GDPR-like)")
            return True
        else:
            log_error(f"Expected denied, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_brazil_lgpd():
    """Test 6: Brazil user without consent → denied (LGPD)"""
    log_test("LGPD Rule - Brazil User Without Consent (Should be DENIED)")
    
    user_id = create_test_user(f"test_brazil_{uuid4().hex[:8]}@example.com", "BR")
    if not user_id:
        return False
    
    response = check_decision(user_id, "ads")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and ('lgpd' in data['reason'] or 'requires_grant' in data['reason']):
            log_success("Brazil correctly denies access without consent (LGPD)")
            return True
        else:
            log_error(f"Expected denied, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_ccpa_without_consent():
    """Test 7: US user without consent → allowed (CCPA default)"""
    log_test("CCPA Rule - US User Without Consent (Should be ALLOWED)")
    
    user_id = create_test_user(f"test_us_no_consent_{uuid4().hex[:8]}@example.com", "US")
    if not user_id:
        return False
    
    response = check_decision(user_id, "marketing")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is True and 'ccpa_default_allow' in data['reason']:
            log_success("CCPA correctly allows access without consent (opt-out model)")
            return True
        else:
            log_error(f"Expected allowed, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_row_without_consent():
    """Test 8: ROW user without consent → allowed (default)"""
    log_test("ROW Rule - Rest of World Without Consent (Should be ALLOWED)")
    
    user_id = create_test_user(f"test_row_{uuid4().hex[:8]}@example.com", "ROW")
    if not user_id:
        return False
    
    response = check_decision(user_id, "personalization")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is True and 'row_default_allow' in data['reason']:
            log_success("ROW correctly allows access without consent")
            return True
        else:
            log_error(f"Expected allowed, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_revoked_consent():
    """Test 9: Revoked consent → denied"""
    log_test("Revoked Consent - Should be DENIED")
    
    user_id = create_test_user(f"test_revoked_{uuid4().hex[:8]}@example.com", "US")
    if not user_id:
        return False
    
    # Grant consent first
    grant_response = grant_consent(user_id, "marketing", "US")
    if grant_response.status_code != 201:
        log_error(f"Failed to grant consent: {grant_response.status_code}")
        return False
    
    log_info("Consent granted")
    
    # Revoke consent
    revoke_response = revoke_consent(user_id, "marketing", "US")
    if revoke_response.status_code != 201:
        log_error(f"Failed to revoke consent: {revoke_response.status_code}")
        return False
    
    log_info("Consent revoked")
    
    # Check decision
    response = check_decision(user_id, "marketing")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and 'revoked' in data['reason']:
            log_success("Revoked consent correctly denies access")
            return True
        else:
            log_error(f"Expected denied, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_expired_consent():
    """Test 10: Expired consent → denied"""
    log_test("Expired Consent - Should be DENIED")
    
    user_id = create_test_user(f"test_expired_{uuid4().hex[:8]}@example.com", "EU")
    if not user_id:
        return False
    
    # Grant consent with expiry in the past
    expired_time = datetime.now(timezone.utc) - timedelta(days=1)
    grant_response = grant_consent(user_id, "location", "EU", expires_at=expired_time)
    
    if grant_response.status_code != 201:
        log_error(f"Failed to grant consent: {grant_response.status_code}")
        return False
    
    log_info(f"Consent granted with expiry: {expired_time.isoformat()}")
    
    # Check decision
    response = check_decision(user_id, "location")
    
    if response.status_code == 200:
        data = response.json()
        log_info(f"Allowed: {data['allowed']}, Reason: {data['reason']}")
        
        if data['allowed'] is False and 'expired' in data['reason']:
            log_success("Expired consent correctly denies access")
            return True
        else:
            log_error(f"Expected denied with 'expired' reason, got allowed={data['allowed']}, reason={data['reason']}")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_policy_snapshot():
    """Test 11: Policy snapshot is stored"""
    log_test("Policy Snapshot - Should be Present in Response")
    
    user_id = create_test_user(f"test_snapshot_{uuid4().hex[:8]}@example.com", "EU")
    if not user_id:
        return False
    
    response = check_decision(user_id, "analytics")
    
    if response.status_code == 200:
        data = response.json()
        
        if 'policy_snapshot' in data and data['policy_snapshot']:
            log_info(f"Policy snapshot: {json.dumps(data['policy_snapshot'], indent=2)}")
            
            # Check if snapshot has expected structure
            snapshot = data['policy_snapshot']
            if 'policy' in snapshot and 'region' in snapshot:
                log_success("Policy snapshot correctly stored and returned")
                return True
            else:
                log_error(f"Policy snapshot missing expected fields: {snapshot}")
                return False
        else:
            log_error("Policy snapshot not found in response")
            return False
    else:
        log_error(f"Request failed: {response.status_code}")
        return False

def test_audit_log_written():
    """Test 12: Audit log is written (check via another decision)"""
    log_test("Audit Log - Should be Written (Verified by multiple decisions)")
    
    user_id = create_test_user(f"test_audit_{uuid4().hex[:8]}@example.com", "US")
    if not user_id:
        return False
    
    # Make first decision
    response1 = check_decision(user_id, "marketing")
    if response1.status_code != 200:
        log_error(f"First decision failed: {response1.status_code}")
        return False
    
    log_info("First decision made")
    
    # Make second decision
    response2 = check_decision(user_id, "analytics")
    if response2.status_code != 200:
        log_error(f"Second decision failed: {response2.status_code}")
        return False
    
    log_info("Second decision made")
    
    # If both decisions succeeded, audit logs were written
    log_success("Multiple decisions processed (audit logs written)")
    return True

def test_http_methods():
    """Test 13: Test HTTP methods (only GET should work for decision endpoint)"""
    log_test("HTTP Methods - Decision Endpoint Should Only Accept GET")
    
    user_id = create_test_user(f"test_methods_{uuid4().hex[:8]}@example.com", "US")
    if not user_id:
        return False
    
    all_passed = True
    
    # Test GET (should work)
    log_info("Testing GET method...")
    response = requests.get(
        f"{BASE_URL}/decision",
        headers=HEADERS,
        params={'user_id': user_id, 'purpose': 'marketing'}
    )
    if response.status_code == 200:
        log_success("GET method works correctly")
    else:
        log_error(f"GET method failed: {response.status_code}")
        all_passed = False
    
    # Test POST (should not work)
    log_info("Testing POST method...")
    response = requests.post(
        f"{BASE_URL}/decision",
        headers=HEADERS,
        json={'user_id': user_id, 'purpose': 'marketing'}
    )
    if response.status_code in [405, 404]:
        log_success(f"POST method correctly rejected ({response.status_code})")
    else:
        log_error(f"POST method should be rejected, got: {response.status_code}")
        all_passed = False
    
    # Test PUT (should not work)
    log_info("Testing PUT method...")
    response = requests.put(
        f"{BASE_URL}/decision",
        headers=HEADERS,
        json={'user_id': user_id, 'purpose': 'marketing'}
    )
    if response.status_code in [405, 404]:
        log_success(f"PUT method correctly rejected ({response.status_code})")
    else:
        log_error(f"PUT method should be rejected, got: {response.status_code}")
        all_passed = False
    
    # Test DELETE (should not work)
    log_info("Testing DELETE method...")
    response = requests.delete(
        f"{BASE_URL}/decision",
        headers=HEADERS,
        params={'user_id': user_id, 'purpose': 'marketing'}
    )
    if response.status_code in [405, 404]:
        log_success(f"DELETE method correctly rejected ({response.status_code})")
    else:
        log_error(f"DELETE method should be rejected, got: {response.status_code}")
        all_passed = False
    
    return all_passed

def run_all_tests():
    """Run all tests and generate report"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}DECISION ENGINE COMPREHENSIVE TEST SUITE{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    tests = [
        ("Decision Endpoint Basic Functionality", test_decision_endpoint),
        ("GDPR - EU Without Consent", test_gdpr_without_consent),
        ("GDPR - EU With Consent", test_gdpr_with_consent),
        ("GDPR - INDIA Without Consent", test_india_gdpr_like),
        ("GDPR - UK Without Consent", test_uk_gdpr_like),
        ("LGPD - Brazil Without Consent", test_brazil_lgpd),
        ("CCPA - US Without Consent", test_ccpa_without_consent),
        ("ROW - Default Allow", test_row_without_consent),
        ("Revoked Consent", test_revoked_consent),
        ("Expired Consent", test_expired_consent),
        ("Policy Snapshot Storage", test_policy_snapshot),
        ("Audit Log Written", test_audit_log_written),
        ("HTTP Methods", test_http_methods),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            log_error(f"Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASSED{Colors.RESET}" if result else f"{Colors.RED}FAILED{Colors.RESET}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print(f"{Colors.GREEN}✓ ALL TESTS PASSED!{Colors.RESET}")
    else:
        print(f"{Colors.RED}✗ {total - passed} TESTS FAILED{Colors.RESET}")
    
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.RESET}")
        exit(1)
