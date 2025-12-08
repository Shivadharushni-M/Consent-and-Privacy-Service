import pytest
from app.models.consent import RegionEnum


class TestGrantConsent:
    def test_grant_consent_success(self, client, test_user, auth_headers):
        response = client.post("/consent/grant", json={"user_id": str(test_user.id), "purpose": "analytics", "region": "EU"}, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["purpose"] == "analytics"
        assert data["status"] == "granted"

    def test_grant_consent_no_auth(self, client, test_user):
        response = client.post("/consent/grant", json={"user_id": str(test_user.id), "purpose": "analytics", "region": "EU"})
        assert response.status_code == 401

    def test_grant_consent_other_user(self, client, test_user, db, auth_headers):
        from app.models.consent import User
        other = User(email="other@example.com", region=RegionEnum.US)
        db.add(other)
        db.commit()
        response = client.post("/consent/grant", json={"user_id": str(other.id), "purpose": "analytics", "region": "US"}, headers=auth_headers)
        assert response.status_code == 403


class TestRevokeConsent:
    def test_revoke_consent_success(self, client, test_user, auth_headers):
        client.post("/consent/grant", json={"user_id": str(test_user.id), "purpose": "analytics", "region": "EU"}, headers=auth_headers)
        response = client.post("/consent/revoke", json={"user_id": str(test_user.id), "purpose": "analytics", "region": "EU"}, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "revoked"


class TestPreferences:
    def test_get_preferences(self, client, test_user, auth_headers):
        response = client.get(f"/consent/preferences/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "preferences" in data
        assert "region" in data

