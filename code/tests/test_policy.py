import unittest

from code.data import load_dataset
from code.policy import category_for_record, evaluate_record
from pathlib import Path


RULES = load_dataset(Path(__file__).resolve().parents[2] / "dataset")["rules"]


class PolicyEvaluationTests(unittest.TestCase):
    def test_classifies_resources_from_system_and_collection_names(self):
        self.assertEqual(
            category_for_record("identity_service", "deleted_customer_references", {}),
            "ACCOUNT_TOMBSTONE",
        )
        self.assertEqual(
            category_for_record("support_platform", "support_attachments", {}),
            "SUPPORT_ATTACHMENT",
        )
        self.assertEqual(
            category_for_record("integration_service", "connectors", {}),
            "DATA_FLOW",
        )

    def test_allows_a_stable_subject_reference_in_a_redacted_tombstone(self):
        result = evaluate_record(
            "ACCOUNT_TOMBSTONE",
            {
                "resource_id": "tombstone_1",
                "subject_reference": "user_1",
                "name": None,
                "email": None,
                "phone": None,
                "email_hash": None,
            },
            "user_1",
            "2026-09-01T00:00:00Z",
            RULES,
        )

        self.assertEqual(result.required_action, "REDACT")
        self.assertEqual(result.state, "REDACTED")
        self.assertFalse(result.violation)

    def test_anonymous_analytics_must_not_retain_a_stable_user_link(self):
        result = evaluate_record(
            "ANALYTICS_PROFILE",
            {
                "resource_id": "analytics_1",
                "user_id": "user_1",
                "email": None,
                "phone": None,
                "email_hash": None,
            },
            "user_1",
            "2026-09-01T00:00:00Z",
            RULES,
        )

        self.assertEqual(result.required_action, "ANONYMIZE")
        self.assertEqual(result.state, "IDENTIFIABLE")
        self.assertTrue(result.violation)

    def test_retained_security_record_is_compliant_before_expiry(self):
        result = evaluate_record(
            "SECURITY_AUDIT_LOG",
            {"retention_until": "2027-01-01T00:00:00Z"},
            "user_1",
            "2026-09-01T00:00:00Z",
            RULES,
        )

        self.assertEqual(result.required_action, "RETAIN")
        self.assertEqual(result.state, "PRESENT")
        self.assertFalse(result.violation)

    def test_backup_with_restore_enabled_is_a_restore_violation(self):
        result = evaluate_record(
            "BACKUP_ARCHIVE",
            {"restore_allowed": True},
            "user_1",
            "2026-09-01T00:00:00Z",
            RULES,
        )

        self.assertEqual(result.required_action, "BLOCK_RESTORE")
        self.assertEqual(result.state, "ACTIVE")
        self.assertTrue(result.violation)

    def test_handover_active_state_is_a_data_flow_violation(self):
        result = evaluate_record(
            "DATA_FLOW", {"state": "ACTIVE"}, "user_1", "2026-09-01T00:00:00Z", RULES
        )
        self.assertEqual(result.state, "ACTIVE")
        self.assertTrue(result.violation)

    def test_eligible_restore_candidate_without_deletion_block_is_a_risk(self):
        result = evaluate_record(
            "BACKUP_ARCHIVE", {"eligible": "true", "deletion_block": "false"},
            "user_17", "2026-09-15T12:00:00Z", RULES,
        )
        self.assertEqual(result.state, "ACTIVE")
        self.assertTrue(result.violation)

    def test_contact_opt_in_record_is_not_an_analytics_profile(self):
        self.assertEqual(
            category_for_record(
                "analytics_platform", "contact_lookup_completed", {"email_opt_in": "true"}
            ),
            "MARKETING_PROFILE",
        )

    def test_support_contact_field_requires_redaction(self):
        result = evaluate_record(
            "SUPPORT_MESSAGE", {"requester_email": "person@example.com"},
            "user_1", "2026-09-01T00:00:00Z", RULES,
        )
        self.assertEqual(result.required_action, "REDACT")
        self.assertTrue(result.violation)

    def test_null_text_is_not_treated_as_direct_pii(self):
        result = evaluate_record(
            "ANALYTICS_PROFILE", {"email": "null", "phone": "null", "email_hash": "null"},
            "user_1", "2026-09-01T00:00:00Z", RULES,
        )
        self.assertEqual(result.state, "ANONYMIZED")
        self.assertFalse(result.violation)


if __name__ == "__main__":
    unittest.main()
