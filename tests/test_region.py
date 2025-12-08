import pytest
from app.models.consent import RegionEnum
from app.services.region_service import detect_region_from_ip, _map_iso_to_region, _is_local_ip


class TestISOMapping:
    @pytest.mark.parametrize("iso,expected", [
        ("US", RegionEnum.US),
        ("IN", RegionEnum.INDIA),
        ("DE", RegionEnum.EU),
        ("FR", RegionEnum.EU),
        ("GB", RegionEnum.UK),
        ("BR", RegionEnum.BR),
        ("CA", RegionEnum.CA),
        ("AU", RegionEnum.AU),
        ("JP", RegionEnum.JP),
        ("XX", RegionEnum.ROW),
        (None, RegionEnum.ROW),
        ("", RegionEnum.ROW),
    ])
    def test_iso_to_region(self, iso, expected):
        assert _map_iso_to_region(iso) == expected


class TestLocalIP:
    @pytest.mark.parametrize("ip,expected", [
        ("127.0.0.1", True),
        ("192.168.1.1", True),
        ("10.0.0.1", True),
        ("172.16.0.1", True),
        ("localhost", True),
        ("::1", True),
        ("8.8.8.8", False),
        ("", True),
    ])
    def test_is_local_ip(self, ip, expected):
        assert _is_local_ip(ip) == expected


class TestRegionEndpoint:
    def test_region_endpoint_requires_auth(self, client):
        response = client.get("/region")
        assert response.status_code == 401

    def test_region_endpoint_with_auth(self, client, auth_headers):
        response = client.get("/region", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ip" in data
        assert "region" in data
        assert "detected" in data

