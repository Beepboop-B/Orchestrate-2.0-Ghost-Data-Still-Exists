import unittest
from pathlib import Path

from code.evidence import parse_evidence_file
from code.state import reconstruct_resource_state


REPO_ROOT = Path(__file__).resolve().parents[2]


class PointInTimeStateTests(unittest.TestCase):
    def test_uses_latest_state_available_at_audit_cutoff(self):
        records = [
            {
                "file_id": "evidence_1",
                "captured_at": "2026-08-01T00:00:00Z",
                "observed_at": "2026-08-01T00:00:00Z",
                "system_id": "search_service",
                "collection": "customer_search_documents",
                "resource_id": "search_1",
                "raw": {"resource_id": "search_1", "email": "old@example.com"},
            },
            {
                "file_id": "evidence_2",
                "captured_at": "2026-08-02T00:00:00Z",
                "observed_at": "2026-08-02T00:00:00Z",
                "system_id": "search_service",
                "collection": "index_queries",
                "resource_id": "search_1",
                "raw": {"result": "not_found", "total_hits": "0"},
            },
            {
                "file_id": "evidence_3",
                "captured_at": "2026-08-04T00:00:00Z",
                "observed_at": "2026-08-04T00:00:00Z",
                "system_id": "search_service",
                "collection": "customer_search_documents",
                "resource_id": "search_1",
                "raw": {"resource_id": "search_1", "email": "old@example.com"},
            },
        ]

        state = reconstruct_resource_state(
            records, "search_1", "search_service", "SEARCH_INDEX_ENTRY", "2026-08-03T00:00:00Z"
        )

        self.assertEqual(state.state, "ABSENT")
        self.assertEqual(state.evidence["file_id"], "evidence_2")

    def test_snapshot_row_wins_a_same_time_scope_absence(self):
        records = [
            {
                "file_id": "evidence_54",
                "captured_at": "2026-09-02T23:00:00Z",
                "observed_at": "2026-09-02T23:00:00Z",
                "system_id": "account_service",
                "collection": "customer_profiles_failover_replica",
                "resource_id": "account_005",
                "raw": {"resource_id": "account_005", "email": "leila@example.com"},
            },
            {
                "file_id": "evidence_54",
                "captured_at": "2026-09-02T23:00:00Z",
                "observed_at": "2026-09-02T23:00:00Z",
                "system_id": "account_service",
                "collection": "customer_profiles_primary",
                "resource_id": None,
                "raw": {"scope": True},
            },
        ]

        state = reconstruct_resource_state(
            records, "account_005", "account_service", "USER_PROFILE", "2026-09-03T00:00:00Z"
        )

        self.assertEqual(state.state, "PRESENT")

    def test_sql_snapshot_scopes_prove_absence_for_a_known_resource(self):
        records = parse_evidence_file(
            REPO_ROOT / "dataset/evidence/databases/customer_accounts_failover_replica_20260902.sql",
            "evidence_54",
            "2026-09-02T23:00:00Z",
        )

        state = reconstruct_resource_state(
            records, "account_001", "account_service", "USER_PROFILE", "2026-09-03T00:00:00Z"
        )

        self.assertEqual(state.state, "ABSENT")
        self.assertEqual(state.evidence["file_id"], "evidence_54")

    def test_lookup_started_event_is_not_record_presence(self):
        records = [{
            "file_id": "evidence_94", "captured_at": "2026-09-26T10:00:00Z",
            "observed_at": "2026-09-26T10:00:00Z", "system_id": "account_service",
            "collection": "profile_lookup_started", "resource_id": "account_1",
            "raw": {"event": "profile_lookup_started", "resource_id": "account_1"},
        }]
        state = reconstruct_resource_state(records, "account_1", "account_service", "USER_PROFILE", "2026-09-27T00:00:00Z")
        self.assertIsNone(state)

    def test_positive_support_pii_scan_is_present_and_trace_linkable(self):
        from code.evidence import _propagate_trace_identity

        scan = {
            "file_id": "evidence_1", "captured_at": "2026-09-15T12:00:00Z",
            "observed_at": "2026-09-15T11:51:08Z", "system_id": "support_platform",
            "collection": "message_pii_scan", "resource_id": "support_1",
            "raw": {"trace_id": "tr-1", "event": "message_pii_scan",
                    "matched_value": "person@example.com", "detector": "direct_identifier"},
        }
        start = {"raw": {"trace_id": "tr-1", "event": "message_scan_started",
                         "subject_key": "person@example.com"}}
        _propagate_trace_identity([start, scan])
        self.assertEqual(scan["raw"].get("subject_key"), "person@example.com")
        state = reconstruct_resource_state(
            [scan], "support_1", "support_platform", "SUPPORT_MESSAGE", "2026-09-15T12:00:00Z"
        )
        self.assertEqual(state.state, "PRESENT")

    def test_completed_read_with_returned_contact_field_is_present(self):
        record = {
            "file_id": "evidence_1", "captured_at": "2026-09-15T12:00:00Z",
            "observed_at": "2026-09-15T11:00:00Z", "system_id": "support_platform",
            "collection": "support_ticket_read_completed", "resource_id": "support_1",
            "raw": {"event": "support_ticket_read_completed", "requester_email": "person@example.com"},
        }
        state = reconstruct_resource_state(
            [record], "support_1", "support_platform", "SUPPORT_MESSAGE", "2026-09-15T12:00:00Z"
        )
        self.assertEqual(state.state, "PRESENT")


if __name__ == "__main__":
    unittest.main()
