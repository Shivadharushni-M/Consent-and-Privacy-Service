import pytest


class TestUserAuth:
    def test_login_success(self, client, test_user):
        response = client.post("/auth/login", json={"email": "test@example.com", "password": "testpass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "user"
        assert data["user_id"] == str(test_user.id)

    def test_login_invalid_credentials(self, client, test_user):
        response = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})
        assert response.status_code == 401
        assert response.json()["detail"] == "invalid_credentials"

    def test_login_nonexistent_user(self, client):
        response = client.post("/auth/login", json={"email": "noone@example.com", "password": "pass"})
        assert response.status_code == 401


class TestAdminAuth:
    def test_admin_login_success(self, client, test_admin):
        response = client.post("/auth/admin/login", json={"email": "admin@example.com", "password": "adminpass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "admin"

    def test_admin_login_invalid(self, client, test_admin):
        response = client.post("/auth/admin/login", json={"email": "admin@example.com", "password": "wrong"})
        assert response.status_code == 401


class TestJWTToken:
    def test_protected_endpoint_with_token(self, client, test_user, auth_headers):
        response = client.get(f"/users/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200

    def test_protected_endpoint_no_token(self, client, test_user):
        response = client.get(f"/users/{test_user.id}")
        assert response.status_code == 401

    def test_admin_endpoint_with_user_token(self, client, auth_headers):
        response = client.get("/admin/audit", headers=auth_headers)
        assert response.status_code == 403

    def test_admin_endpoint_with_admin_token(self, client, admin_headers):
        response = client.get("/admin/audit", headers=admin_headers)
        assert response.status_code == 200

