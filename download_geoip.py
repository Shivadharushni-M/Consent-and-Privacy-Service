#!/usr/bin/env python3
"""
Script to download MaxMind GeoLite2-Country database
Uses credentials from .env file
"""
import os
import sys
import tarfile
from pathlib import Path
from dotenv import load_dotenv

try:
    import httpx
except ImportError:
    try:
        import requests as httpx
    except ImportError:
        print("ERROR: Need either 'httpx' or 'requests' library installed")
        print("Run: pip install httpx")
        sys.exit(1)

# Load environment variables
load_dotenv()

MAXMIND_ACCOUNT_ID = os.getenv("MAXMIND_ACCOUNT_ID")
MAXMIND_LICENSE_KEY = os.getenv("MAXMIND_LICENSE_KEY")

if not MAXMIND_ACCOUNT_ID or not MAXMIND_LICENSE_KEY:
    print("ERROR: MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY must be set in .env file")
    sys.exit(1)

# Setup paths
BASE_DIR = Path(__file__).resolve().parent
GEOIP_DIR = BASE_DIR / "app" / "geoip"
GEOIP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = GEOIP_DIR / "GeoLite2-Country.mmdb"
TEMP_TAR = BASE_DIR / "GeoLite2-Country.tar.gz"

# MaxMind download URL
DOWNLOAD_URL = f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key={MAXMIND_LICENSE_KEY}&suffix=tar.gz"

print("=" * 60)
print("MaxMind GeoIP Database Downloader")
print("=" * 60)
print(f"Account ID: {MAXMIND_ACCOUNT_ID}")
print(f"Download URL: {DOWNLOAD_URL}")
print(f"Target directory: {GEOIP_DIR}")
print(f"Database file: {DB_PATH}")
print()

try:
    # Download the database
    print("Downloading GeoLite2-Country database...")
    print("This may take a few minutes...")
    
    # Use httpx or requests
    if hasattr(httpx, 'Client'):
        # httpx
        with httpx.Client(timeout=300.0, auth=(MAXMIND_ACCOUNT_ID, MAXMIND_LICENSE_KEY)) as client:
            response = client.get(DOWNLOAD_URL)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            with open(TEMP_TAR, 'wb') as f:
                f.write(response.content)
                downloaded = len(response.content)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)")
    else:
        # requests
        response = httpx.get(
            DOWNLOAD_URL,
            auth=(MAXMIND_ACCOUNT_ID, MAXMIND_LICENSE_KEY),
            timeout=300,
            stream=True
        )
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(TEMP_TAR, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
    
    print("\nDownload complete!")
    print()
    
    # Extract the database file
    print("Extracting database file...")
    with tarfile.open(TEMP_TAR, 'r:gz') as tar:
        # Find the .mmdb file in the archive
        mmdb_members = [m for m in tar.getmembers() if m.name.endswith('GeoLite2-Country.mmdb')]
        
        if not mmdb_members:
            print("ERROR: Could not find GeoLite2-Country.mmdb in the downloaded archive")
            sys.exit(1)
        
        # Extract the database file
        mmdb_member = mmdb_members[0]
        print(f"Found: {mmdb_member.name}")
        
        # Extract to target location
        with tar.extractfile(mmdb_member) as source:
            with open(DB_PATH, 'wb') as target:
                target.write(source.read())
    
    print(f"Database extracted to: {DB_PATH}")
    print()
    
    # Clean up temporary file
    if TEMP_TAR.exists():
        TEMP_TAR.unlink()
        print("Cleaned up temporary files")
    
    # Verify the file exists and has content
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        file_size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        print("=" * 60)
        print("SUCCESS! GeoIP database is ready.")
        print(f"File size: {file_size_mb:.2f} MB")
        print(f"Location: {DB_PATH}")
        print()
        print("The service will automatically use this database on next restart.")
        print("=" * 60)
    else:
        print("ERROR: Database file was not created or is empty")
        sys.exit(1)

except Exception as e:
    error_type = str(type(e))
    if "RequestException" in error_type or "HTTP" in error_type or "Connection" in error_type or "Timeout" in error_type:
        print(f"ERROR: Failed to download database: {e}")
        print()
        print("Possible issues:")
        print("1. Invalid MaxMind credentials")
        print("2. Network connection problem")
        print("3. MaxMind service unavailable")
    else:
        print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
