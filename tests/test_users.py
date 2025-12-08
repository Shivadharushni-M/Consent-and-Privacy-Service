import pytest
from app.models.consent import RegionEnum


class TestCreateUser:
    def test_create_user_self_register(self, client):
        response = client.post("/users", json={"email": "new@example.com", "password": "newpass", "region": "US"})
        assert response.status_code == 201
        assert response.json()["email"] == "new@example.com"

    def test_create_user_duplicate_email(self, client, test_user):
        response = client.post("/users", json={"email": "test@example.com", "password": "pass", "region": "EU"})
        assert response.status_code == 409  # Conflict


class TestGetUser:
    def test_get_user_with_token(self, client, test_user, auth_headers):
        response = client.get(f"/users/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_get_user_no_auth(self, client, test_user):
        response = client.get(f"/users/{test_user.id}")
        assert response.status_code == 401

    def test_admin_can_get_any_user(self, client, test_user, admin_headers):
        response = client.get(f"/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 200

