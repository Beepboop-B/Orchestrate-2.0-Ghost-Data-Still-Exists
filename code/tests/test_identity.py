import unittest

from code.identity import identifiers_for_user, resolve_email


class ResolveEmailTests(unittest.TestCase):
    def test_collects_current_and_historical_identifiers_only_through_cutoff(self):
        identities = [
            {
                "user_id": "user_1",
                "name": "Amina Example",
                "email": "current@example.com",
                "phone": "+1-555-0100",
                "email_hash": "hash-current",
                "updated_at": "2026-02-01T00:00:00Z",
            }
        ]
        audit_log = [
            {
                "user_id": "user_1",
                "field_name": "email",
                "old_value": "old@example.com",
                "new_value": "current@example.com",
                "event_time": "2026-01-01T00:00:00Z",
            },
            {
                "user_id": "user_1",
                "field_name": "phone",
                "old_value": "+1-555-0099",
                "new_value": "+1-555-0100",
                "event_time": "2026-01-01T00:00:00Z",
            },
            {
                "user_id": "user_1",
                "field_name": "email_hash",
                "old_value": "hash-old",
                "new_value": "hash-current",
                "event_time": "2026-03-01T00:00:00Z",
            },
        ]

        result = identifiers_for_user(
            "user_1", identities, audit_log, "2026-02-15T00:00:00Z"
        )

        self.assertEqual(result["email"], {"old@example.com", "current@example.com"})
        self.assertEqual(result["phone"], {"15550099", "15550100"})
        self.assertEqual(result["email_hash"], {"hash-current"})
        self.assertEqual(result["name"], {"amina example"})

    def test_resolves_a_historical_email_using_a_change_before_audit_cutoff(self):
        identities = [
            {
                "user_id": "user_1",
                "email": "new@example.com",
                "updated_at": "2026-03-01T00:00:00Z",
            }
        ]
        audit_log = [
            {
                "user_id": "user_1",
                "field_name": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
                "event_time": "2026-02-01T00:00:00Z",
            }
        ]

        result = resolve_email(
            " OLD@example.com ", identities, audit_log, "2026-02-15T00:00:00Z"
        )

        self.assertEqual(result, "user_1")

    def test_does_not_resolve_an_email_first_introduced_after_audit_cutoff(self):
        identities = [
            {
                "user_id": "user_1",
                "email": "new@example.com",
                "updated_at": "2026-03-01T00:00:00Z",
            }
        ]
        audit_log = [
            {
                "user_id": "user_1",
                "field_name": "email",
                "old_value": "old@example.com",
                "new_value": "new@example.com",
                "event_time": "2026-03-01T00:00:00Z",
            }
        ]

        result = resolve_email(
            "new@example.com", identities, audit_log, "2026-02-15T00:00:00Z"
        )

        self.assertIsNone(result)

    def test_returns_none_when_email_matches_multiple_users(self):
        identities = [
            {
                "user_id": "user_1",
                "email": "same@example.com",
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "user_id": "user_2",
                "email": "SAME@example.com",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ]

        result = resolve_email(
            "same@example.com", identities, [], "2026-02-15T00:00:00Z"
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
