import pytest
from datetime import timedelta
from app.models.consent import ConsentHistory, PurposeEnum, StatusEnum, RegionEnum
from app.jobs.retention import _mark_expired_consents
from app.utils.helpers import get_utc_now


class TestMarkExpiredConsents:
    def test_marks_expired_consents(self, db, test_user):
        past = get_utc_now() - timedelta(days=1)
        consent = ConsentHistory(user_id=test_user.id, purpose=PurposeEnum.ANALYTICS, status=StatusEnum.GRANTED, region=RegionEnum.EU, valid_until=past)
        db.add(consent)
        db.commit()
        count = _mark_expired_consents(db)
        assert count == 1
        db.refresh(consent)
        assert consent.status == StatusEnum.EXPIRED

    def test_ignores_non_expired(self, db, test_user):
        future = get_utc_now() + timedelta(days=30)
        consent = ConsentHistory(user_id=test_user.id, purpose=PurposeEnum.ANALYTICS, status=StatusEnum.GRANTED, region=RegionEnum.EU, valid_until=future)
        db.add(consent)
        db.commit()
        count = _mark_expired_consents(db)
        assert count == 0


class TestRetentionEndpoint:
    def test_retention_requires_admin(self, client, auth_headers):
        response = client.get("/retention/run", headers=auth_headers)
        assert response.status_code == 403

    def test_retention_with_admin(self, client, admin_headers):
        response = client.get("/retention/run", headers=admin_headers)
        assert response.status_code == 200

