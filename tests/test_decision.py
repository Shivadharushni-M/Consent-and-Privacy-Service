import pytest
from app.models.consent import PurposeEnum, RegionEnum, StatusEnum
from app.services.decision_service import decide, _policy_allows


class TestPolicyAllows:
    @pytest.mark.parametrize("region,purpose,status,expected", [
        (RegionEnum.EU, PurposeEnum.ANALYTICS, StatusEnum.GRANTED, (True, "gdpr_granted")),
        (RegionEnum.EU, PurposeEnum.ANALYTICS, None, (False, "gdpr_requires_grant")),
        (RegionEnum.EU, PurposeEnum.ANALYTICS, StatusEnum.REVOKED, (False, "gdpr_requires_grant")),  # Sensitive purpose requires explicit grant
        (RegionEnum.US, PurposeEnum.ANALYTICS, None, (True, "ccpa_default_allow")),
        (RegionEnum.US, PurposeEnum.ANALYTICS, StatusEnum.REVOKED, (False, "ccpa_revoked")),
        (RegionEnum.BR, PurposeEnum.ANALYTICS, StatusEnum.GRANTED, (True, "lgpd_granted")),
        (RegionEnum.ROW, PurposeEnum.ANALYTICS, None, (True, "row_default_allow")),
    ])
    def test_policy_rules(self, region, purpose, status, expected):
        assert _policy_allows(region, purpose, status) == expected


class TestDecisionService:
    def test_decide_gdpr_no_consent(self, db, test_user):
        result = decide(db, test_user.id, PurposeEnum.ANALYTICS)
        assert result["allowed"] is False
        assert "gdpr" in result["reason"]

    def test_decide_creates_audit_log(self, db, test_user):
        from app.models.audit import AuditLog
        initial_count = db.query(AuditLog).count()
        decide(db, test_user.id, PurposeEnum.ANALYTICS)
        assert db.query(AuditLog).count() == initial_count + 1

    def test_decide_returns_policy_snapshot(self, db, test_user):
        result = decide(db, test_user.id, PurposeEnum.ANALYTICS)
        assert "policy_snapshot" in result
        assert result["policy_snapshot"] is not None

