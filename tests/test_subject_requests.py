import pytest
from app.models.consent import RequestTypeEnum


class TestSubjectRequests:
    def test_create_export_request(self, client, test_user, auth_headers):
        response = client.post("/subject-requests", json={"user_id": str(test_user.id), "request_type": "export"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["request_type"] == "export"
        assert data["status"] == "pending_verification"
        assert "verification_token" in data

    def test_create_access_request(self, client, test_user, auth_headers):
        response = client.post("/subject-requests", json={"user_id": str(test_user.id), "request_type": "access"}, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["request_type"] == "access"

    def test_create_delete_request(self, client, test_user, auth_headers):
        response = client.post("/subject-requests", json={"user_id": str(test_user.id), "request_type": "delete"}, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["request_type"] == "delete"

    def test_create_rectify_request(self, client, test_user, auth_headers):
        response = client.post("/subject-requests", json={"user_id": str(test_user.id), "request_type": "rectify", "region": "US"}, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["request_type"] == "rectify"

    def test_request_for_other_user_forbidden(self, client, db, auth_headers):
        from app.models.consent import User, RegionEnum
        other = User(email="other@example.com", region=RegionEnum.US)
        db.add(other)
        db.commit()
        response = client.post("/subject-requests", json={"user_id": str(other.id), "request_type": "export"}, headers=auth_headers)
        assert response.status_code == 403

