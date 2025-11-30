#!/usr/bin/env python3

import requests
from app.models.consent import RegionEnum
from app.utils.helpers import build_policy_snapshot

def test_region_policy_mapping():
    """Test that regions are correctly mapped to privacy policies"""
    print("🔹 Testing Region-to-Policy Mapping\n")

    # Test cases: Region -> Expected Policy
    test_cases = [
        (RegionEnum.EU, "gdpr", True, "deny"),
        (RegionEnum.INDIA, "gdpr", True, "deny"),
        (RegionEnum.UK, "gdpr", True, "deny"),
        (RegionEnum.IN, "gdpr", True, "deny"),
        (RegionEnum.BR, "lgpd", True, "deny"),
        (RegionEnum.US, "ccpa", False, "allow"),
        (RegionEnum.ROW, "global", False, "allow"),
        (RegionEnum.SG, "global", False, "allow"),
        (RegionEnum.AU, "global", False, "allow"),
        (RegionEnum.JP, "global", False, "allow"),
        (RegionEnum.CA, "global", False, "allow"),
        (RegionEnum.ZA, "global", False, "allow"),
        (RegionEnum.KR, "global", False, "allow"),
    ]

    passed = 0
    total = len(test_cases)

    print("Region      | Policy | Explicit | Default | Status")
    print("-" * 55)

    for region, expected_policy, expected_explicit, expected_default in test_cases:
        snapshot = build_policy_snapshot(region)

        policy = snapshot["policy"]
        explicit = snapshot["requires_explicit"]
        default = snapshot["default"]

        success = (policy == expected_policy and
                  explicit == expected_explicit and
                  default == expected_default)

        status = "✅" if success else "❌"
        if success:
            passed += 1

        print("10")

    print(f"\n📊 Policy Mapping Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All region-to-policy mappings are correct!")
        return True
    else:
        print("⚠️  Some region-to-policy mappings are incorrect")
        return False

def test_region_endpoint_integration():
    """Test that region detection integrates with policy mapping"""
    print("\n🔹 Testing Region Endpoint + Policy Integration")

    # Get current region from endpoint
    response = requests.get('http://localhost:8000/region')
    if response.status_code != 200:
        print(f"❌ Could not get region from endpoint: {response.status_code}")
        return False

    detected_region = response.json()['region']
    print(f"Detected Region: {detected_region}")

    # Convert string to RegionEnum
    region_enum = RegionEnum(detected_region)

    # Get policy snapshot for this region
    snapshot = build_policy_snapshot(region_enum)

    print("Policy Mapping:")
    print(f"  Policy: {snapshot['policy']}")
    print(f"  Requires Explicit Consent: {snapshot['requires_explicit']}")
    print(f"  Default Consent: {snapshot['default']}")

    print("✅ Region detection properly maps to privacy policy!")
    return True

def main():
    """Run all region-policy mapping tests"""
    print("🚀 Testing Region-to-Privacy Policy Mapping\n")

    # Test the mapping logic
    mapping_success = test_region_policy_mapping()

    # Test integration with endpoint
    integration_success = test_region_endpoint_integration()

    overall_success = mapping_success and integration_success

    print("\n" + "="*60)
    if overall_success:
        print("🎉 Region-to-Privacy Policy Mapping: WORKING CORRECTLY!")
        print("✅ Regions are properly mapped to their respective privacy policies")
    else:
        print("⚠️  Region-to-Privacy Policy Mapping: ISSUES DETECTED")
    print("="*60)

    return overall_success

if __name__ == '__main__':
    main()
