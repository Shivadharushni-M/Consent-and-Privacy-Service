#!/usr/bin/env python3

import requests

BASE_URL = 'http://localhost:8000'

def test_get_region_auto():
    """Test GET /region with auto-detection"""
    print("🔹 Testing GET /region (auto-detection)")

    response = requests.get(f'{BASE_URL}/region')

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Region auto-detected successfully!")
        print(f"Detected Region: {data['region']}")
        return data['region']
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_get_region_with_ip(ip_address, expected_region=None):
    """Test GET /region with specific IP"""
    print(f"\n🔹 Testing GET /region?ip={ip_address}")

    response = requests.get(f'{BASE_URL}/region?ip={ip_address}')

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Region detected successfully!")
        print(f"IP: {ip_address}")
        print(f"Detected Region: {data['region']}")

        if expected_region:
            if data['region'] == expected_region:
                print(f"✅ Correctly detected {expected_region}")
                return True
            else:
                print(f"❌ Expected {expected_region}, got {data['region']}")
                return False
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def main():
    """Test region detection endpoint"""
    print("🚀 Testing Region Detection Endpoint\n")

    results = []

    # Test auto-detection
    auto_region = test_get_region_auto()
    results.append(("Auto-detection", auto_region is not None))

    # Test with known IP addresses for different regions
    test_cases = [
        # Indian IPs (should detect INDIA)
        ("103.0.0.1", "INDIA"),
        ("49.32.0.1", "INDIA"),
        ("117.0.0.1", "INDIA"),

        # US IPs (should detect US)
        ("8.0.0.1", "US"),
        ("192.168.1.1", "ROW"),  # Local/private IP should fallback to ROW

        # European IPs (should detect EU)
        ("2.16.0.1", "EU"),  # Akamai range covering EU

        # Invalid IP
        ("invalid.ip", "ROW"),  # Should fallback to ROW
    ]

    for ip, expected in test_cases:
        success = test_get_region_with_ip(ip, expected)
        results.append((f"IP {ip} → {expected}", success))

    # Summary
    print("\n" + "="*50)
    print("📊 REGION DETECTION TEST SUMMARY")
    print("="*50)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if success:
            passed += 1

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All region detection tests passed!")
        return True
    else:
        print("⚠️  Some region detection tests failed")
        return False

if __name__ == '__main__':
    main()
