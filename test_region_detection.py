#!/usr/bin/env python3
"""Test Region Detection for India"""
from app.services.region_service import detect_region_from_ip, _get_public_ip, _lightweight_region
from app.models.consent import RegionEnum

print("=== REGION DETECTION TEST ===")

# Test public IP detection
print("\n1. Testing public IP detection...")
public_ip = _get_public_ip()
print(f"Detected public IP: {public_ip}")

# Test region detection
print("\n2. Testing region detection...")
if public_ip:
    region = detect_region_from_ip(public_ip)
    print(f"Region for {public_ip}: {region}")

    # Test lightweight method
    lightweight_region = _lightweight_region(public_ip)
    print(f"Lightweight detection result: {lightweight_region}")

# Test with a known Indian IP
indian_ip = "103.5.134.1"  # Known Indian IP range
print(f"\n3. Testing with known Indian IP: {indian_ip}")
region_indian = detect_region_from_ip(indian_ip)
print(f"Region for Indian IP: {region_indian}")

# Test with EU IP
eu_ip = "2.16.1.1"  # Known EU IP range
print(f"\n4. Testing with known EU IP: {eu_ip}")
region_eu = detect_region_from_ip(eu_ip)
print(f"Region for EU IP: {region_eu}")

print("\n=== Expected Results ===")
print(f"Indian IP should return: {RegionEnum.INDIA}")
print(f"EU IP should return: {RegionEnum.EU}")

print("\n=== TEST COMPLETE ===")
