import unittest

from code.audit import (
    find_exact_account_owners, find_matching_evidence,
    find_status_consistent_account_hints,
)
from code.engine import audit_request


class EvidenceLinkingTests(unittest.TestCase):
    @staticmethod
    def _time_only_account_fixture(activities):
        request = {
            "case_id": "case_test", "email": "person@example.com",
            "requested_at": "2026-08-20T10:00:00Z",
            "reported_at": "2026-08-20T11:59:00Z",
            "audit_at": "2026-08-20T12:00:00Z",
            "request_text": "Please delete my account and data.",
        }
        dataset = {
            "identities": [{"user_id": "user_1", "name": "Person Example",
                             "email": "person@example.com", "phone": "",
                             "email_hash": "", "updated_at": "2026-08-01T00:00:00Z"}],
            "audit_log": [],
            "rules": [{"data_category": "USER_PROFILE", "required_action": "DELETE"}],
            "activities": activities,
        }
        evidence = [{"file_id": "evidence_scope", "captured_at": "2026-08-20T11:59:30Z",
                     "observed_at": "2026-08-20T11:59:30Z", "system_id": "account_service",
                     "collection": "snapshot_scope", "raw": {"scope": True,
                     "scope_system": "account_service", "scope_collection": "customer_profiles"}}]

        return request, dataset, evidence

    def test_unique_workflow_activity_and_independent_absence_scope_support_candidate(self):
        activities = [{"activity_id": "activity_1", "event_time": "2026-08-20T11:59:01Z",
                       "event_type": "DELETE_RECORD", "target_system": "account_service",
                       "resource_id": "account_001", "reported_result": "SUCCESS"}]
        request, dataset, evidence = self._time_only_account_fixture(activities)
        request["reported_status"] = "PARTIALLY_COMPLETE"

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "COMPLETE")
        self.assertEqual(
            [(s["resource_id"], s["operation"], s["evidence_id"]) for s in result["steps"]],
            [("account_001", "VERIFY_RECORD_ABSENT", "evidence_scope")],
        )

    def test_multiple_matching_events_are_ambiguous(self):
        activities = [
            {"activity_id": f"activity_{n}", "event_time": f"2026-08-20T11:59:0{n}Z",
             "event_type": "DELETE_RECORD", "target_system": "account_service",
             "resource_id": f"account_00{n}", "reported_result": "SUCCESS"}
            for n in (1, 2)
        ]
        request, dataset, evidence = self._time_only_account_fixture(activities)

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_same_activity_window_for_two_requests_is_ambiguous(self):
        activities = [{"activity_id": "activity_1", "event_time": "2026-08-20T11:59:01Z",
                       "event_type": "DELETE_RECORD", "target_system": "account_service",
                       "resource_id": "account_001", "reported_result": "SUCCESS"}]
        request, dataset, evidence = self._time_only_account_fixture(activities)
        other = dict(request, case_id="case_other", email="other@example.com")
        dataset["request_universe"] = [request, other]

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_after_cutoff_activity_cannot_create_candidate(self):
        activities = [{"activity_id": "activity_1", "event_time": "2026-08-20T12:00:01Z",
                       "event_type": "DELETE_RECORD", "target_system": "account_service",
                       "resource_id": "account_001", "reported_result": "SUCCESS"}]
        request, dataset, evidence = self._time_only_account_fixture(activities)

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_candidate_requires_independent_cutoff_eligible_absence_state(self):
        activities = [{"activity_id": "activity_1", "event_time": "2026-08-20T11:59:01Z",
                       "event_type": "DELETE_RECORD", "target_system": "account_service",
                       "resource_id": "account_001", "reported_result": "SUCCESS"}]
        request, dataset, evidence = self._time_only_account_fixture(activities)
        evidence[0]["captured_at"] = "2026-08-20T12:00:01Z"
        evidence[0]["observed_at"] = "2026-08-20T12:00:01Z"

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_explicit_subject_resource_evidence_supports_account_verification(self):
        request = {
            "case_id": "case_test", "email": "person@example.com",
            "requested_at": "2026-08-20T10:00:00Z",
            "reported_at": "2026-08-20T11:00:00Z",
            "audit_at": "2026-08-20T12:00:00Z",
            "request_text": "Please delete my account and data.",
        }
        dataset = {
            "identities": [{"user_id": "user_1", "name": "Person Example",
                             "email": "person@example.com", "phone": "",
                             "email_hash": "", "updated_at": "2026-08-01T00:00:00Z"}],
            "audit_log": [],
            "rules": [{"data_category": "USER_PROFILE", "required_action": "DELETE"}],
            "activities": [],
        }
        evidence = [{"file_id": "evidence_1", "captured_at": "2026-08-20T11:30:00Z",
                     "observed_at": "2026-08-20T11:30:00Z", "system_id": "account_service",
                     "resource_id": "account_001", "collection": "customer_profiles",
                     "raw": {"user_id": "user_1", "state": "ABSENT"}}]

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "COMPLETE")
        self.assertEqual([(step["resource_id"], step["operation"], step["evidence_id"])
                          for step in result["steps"]],
                         [("account_001", "VERIFY_RECORD_ABSENT", "evidence_1")])

    def test_pre_request_account_identity_link_cannot_support_later_state(self):
        request, dataset, _ = self._time_only_account_fixture([])
        evidence = [
            {"file_id": "old_link", "captured_at": "2026-08-01T00:00:00Z",
             "observed_at": "2026-08-01T00:00:00Z", "system_id": "account_service",
             "resource_id": "account_old", "collection": "customer_profiles",
             "raw": {"user_id": "user_1", "state": "PRESENT"}},
            {"file_id": "scope", "captured_at": "2026-08-20T11:59:30Z",
             "observed_at": "2026-08-20T11:59:30Z", "system_id": "account_service",
             "collection": "snapshot_scope", "raw": {"scope": True,
             "scope_system": "account_service", "scope_collection": "customer_profiles"}},
        ]

        result = audit_request(request, dataset, evidence)

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_exact_account_owner_uses_exact_identity_values(self):
        requests = [
            {"case_id": "owner", "email": "person@example.com",
             "audit_at": "2026-08-20T12:00:00Z"},
            {"case_id": "other", "email": "other@example.com",
             "audit_at": "2026-08-20T12:00:00Z"},
        ]
        identities = [
            {"user_id": "user_1", "email": "person@example.com", "updated_at": "2026-08-01T00:00:00Z"},
            {"user_id": "user_2", "email": "other@example.com", "updated_at": "2026-08-01T00:00:00Z"},
        ]
        evidence = [{"file_id": "e1", "captured_at": "2026-08-20T11:00:00Z",
                     "observed_at": "2026-08-20T11:00:00Z", "system_id": "account_service",
                     "resource_id": "account_001", "raw": {"user_id": "user_1"}},
                    {"file_id": "e2", "captured_at": "2026-08-20T11:00:00Z",
                     "observed_at": "2026-08-20T11:00:00Z", "system_id": "account_service",
                     "resource_id": "account_002", "raw": {"email": "other@example.com"}},
                    {"file_id": "e3", "captured_at": "2026-08-20T11:00:00Z",
                     "observed_at": "2026-08-20T11:00:00Z", "system_id": "account_service",
                     "resource_id": "account_003", "raw": {"lookup_key": "prefixperson@example.com"}},
                    {"file_id": "e4", "captured_at": "2026-08-20T11:00:00Z",
                     "observed_at": "2026-08-20T11:00:00Z", "system_id": "account_service",
                     "resource_id": "account_004", "raw": {"text": "owner=person@example.com"}},
                    {"file_id": "e5", "captured_at": "2026-08-20T11:00:00Z",
                     "observed_at": "2026-08-20T11:00:00Z", "system_id": "account_service",
                     "resource_id": "account_005", "raw": {"requester_phone": "+1 212-555-0199"}}]

        history = [{"user_id": "user_1", "event_time": "2026-07-01T00:00:00Z",
                    "field_name": "phone", "old_value": "+1 (212) 555-0199",
                    "new_value": "+1 (212) 555-0100"}]
        owners = find_exact_account_owners(evidence, requests, identities, history)

        self.assertEqual(owners, {"account_001": {"owner"}, "account_002": {"other"},
                                  "account_004": {"owner"}, "account_005": {"owner"}})

    def test_status_consistent_account_hint_requires_matching_result_and_time(self):
        request = {
            "case_id": "case_complete", "reported_status": "COMPLETE",
            "requested_at": "2026-08-20T08:00:00Z",
            "reported_at": "2026-08-20T10:00:00Z",
            "audit_at": "2026-08-20T12:00:00Z",
        }
        activities = [
            {"activity_id": "a_success", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_001",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "SUCCESS"},
            {"activity_id": "a_failed", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_002",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "FAILED"},
            {"activity_id": "a_late", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_003",
             "event_time": "2026-08-20T08:30:00Z", "reported_result": "SUCCESS"},
        ]

        hints = find_status_consistent_account_hints(activities, [request])

        self.assertEqual(hints, {"case_complete": ("account_001", "a_success")})

    def test_status_consistent_hint_still_requires_independent_cutoff_state(self):
        request = {
            "case_id": "case_test", "email": "person@example.com",
            "requested_at": "2026-08-20T08:00:00Z",
            "reported_at": "2026-08-20T10:00:00Z",
            "audit_at": "2026-08-20T12:00:00Z",
            "request_text": "Please delete my account and data.",
        }
        dataset = {
            "identities": [{"user_id": "user_1", "name": "Person Example",
                             "email": "person@example.com", "phone": "",
                             "email_hash": "", "updated_at": "2026-08-01T00:00:00Z"}],
            "audit_log": [],
            "rules": [{"data_category": "USER_PROFILE", "required_action": "DELETE"}],
            "activities": [],
            "account_link_hints": {"case_test": ("account_001", "activity_1")},
        }

        result = audit_request(request, dataset, [])

        self.assertEqual(result["deletion_status"], "INCOMPLETE")
        self.assertEqual(result["steps"], [])

    def test_status_consistent_hint_maps_partial_and_not_started_results(self):
        requests = [
            {"case_id": "partial", "reported_status": "PARTIALLY_COMPLETE",
             "requested_at": "2026-08-20T08:00:00Z", "reported_at": "2026-08-20T10:00:00Z",
             "audit_at": "2026-08-20T12:00:00Z"},
            {"case_id": "not_started", "reported_status": "NOT_STARTED",
             "requested_at": "2026-08-20T08:00:00Z", "reported_at": "2026-08-20T10:00:00Z",
             "audit_at": "2026-08-20T12:00:00Z"},
        ]
        activities = [
            {"activity_id": "partial_success", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_001",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "SUCCESS"},
            {"activity_id": "partial_partial", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_002",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "PARTIAL"},
            {"activity_id": "not_started_failed", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_003",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "FAILED"},
            {"activity_id": "not_started_partial", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_004",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "PARTIAL"},
        ]

        hints = find_status_consistent_account_hints(activities, requests)
        self.assertEqual(hints, {"not_started": ("account_003", "not_started_failed")})
        self.assertEqual(
            find_status_consistent_account_hints(activities[:1], requests[:1]),
            {"partial": ("account_001", "partial_success")},
        )
        self.assertEqual(
            find_status_consistent_account_hints(activities[1:2], requests[:1]),
            {"partial": ("account_002", "partial_partial")},
        )

    def test_one_to_one_hint_propagation_and_ambiguous_claims(self):
        first = {"case_id": "first", "reported_status": "COMPLETE",
                 "requested_at": "2026-08-20T07:00:00Z", "reported_at": "2026-08-20T10:00:00Z",
                 "audit_at": "2026-08-20T12:00:00Z"}
        second = {"case_id": "second", "reported_status": "COMPLETE",
                  "requested_at": "2026-08-20T07:00:00Z", "reported_at": "2026-08-20T09:50:00Z",
                  "audit_at": "2026-08-20T12:00:00Z"}
        activities = [
            {"activity_id": "shared", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_001",
             "event_time": "2026-08-20T09:00:00Z", "reported_result": "SUCCESS"},
            {"activity_id": "second_only", "event_type": "DELETE_RECORD",
             "target_system": "account_service", "resource_id": "account_002",
             "event_time": "2026-08-20T08:35:00Z", "reported_result": "SUCCESS"},
        ]

        hints = find_status_consistent_account_hints(activities, [first, second])
        self.assertEqual(hints, {
            "first": ("account_001", "shared"),
            "second": ("account_002", "second_only"),
        })

        ambiguous = find_status_consistent_account_hints(
            [activities[0]], [first, dict(first, case_id="ambiguous")]
        )
        self.assertEqual(ambiguous, {})

    def test_matches_historical_identifiers_but_excludes_post_cutoff_evidence(self):
        records = [
            {
                "file_id": "evidence_1",
                "captured_at": "2026-02-01T00:00:00Z",
                "observed_at": "2026-02-01T00:00:00Z",
                "raw": {"email": "old@example.com", "resource_id": "search_1"},
            },
            {
                "file_id": "evidence_2",
                "captured_at": "2026-04-01T00:00:00Z",
                "observed_at": "2026-04-01T00:00:00Z",
                "raw": {"email": "old@example.com", "resource_id": "search_2"},
            },
        ]
        identifiers = {
            "user_id": {"user_1"},
            "email": {"old@example.com", "new@example.com"},
            "phone": set(),
            "email_hash": set(),
            "name": set(),
        }

        matches = find_matching_evidence(records, identifiers, "2026-03-01T00:00:00Z")

        self.assertEqual([r["file_id"] for r in matches], ["evidence_1"])

    def test_matches_name_only_business_document(self):
        records = [{
            "file_id": "evidence_58", "captured_at": "2026-09-12T07:30:00Z",
            "observed_at": "2026-09-12T07:30:00Z", "text": "Delivery correction for Priya Raman",
            "raw": {}, "system_id": "support_platform", "resource_id": "support_001",
        }]
        identifiers = {"name": {"priya raman"}, "email": set(), "phone": set(),
                       "email_hash": set(), "user_id": set()}
        matches = find_matching_evidence(records, identifiers, "2026-09-13T00:00:00Z")
        self.assertEqual(len(matches), 1)

    def test_matches_trace_subject_ref_and_correlation_key_aliases(self):
        records = [
            {"file_id": "evidence_1", "captured_at": "2026-09-15T11:59:39Z",
             "observed_at": "2026-09-15T11:59:37Z", "raw": {"subject_ref": "user_15"}},
            {"file_id": "evidence_2", "captured_at": "2026-09-15T11:59:39Z",
             "observed_at": "2026-09-15T11:58:11Z", "raw": {"subject_key": "old@example.com"}},
            {"file_id": "evidence_3", "captured_at": "2026-09-15T11:59:39Z",
             "observed_at": "2026-09-15T11:58:26Z", "raw": {"correlation_key": "hash123"}},
        ]
        identifiers = {"user_id": {"user_15"}, "email": {"old@example.com"},
                       "email_hash": {"hash123"}, "phone": set(), "name": set()}
        matches = find_matching_evidence(records, identifiers, "2026-09-15T12:00:00Z")
        self.assertEqual({row["file_id"] for row in matches}, {"evidence_1", "evidence_2", "evidence_3"})

    def test_lookup_fields_match_exact_stable_ids_emails_hashes_and_phones(self):
        records = [
            {"file_id": "user", "captured_at": "2026-09-15T11:00:00Z",
             "observed_at": "2026-09-15T10:59:00Z", "raw": {"lookup_key": "user_15"}},
            {"file_id": "email", "captured_at": "2026-09-15T11:00:00Z",
             "observed_at": "2026-09-15T10:59:00Z", "raw": {"query": "old@example.com"}},
            {"file_id": "hash", "captured_at": "2026-09-15T11:00:00Z",
             "observed_at": "2026-09-15T10:59:00Z", "raw": {"subject_key": "hash-15"}},
            {"file_id": "phone", "captured_at": "2026-09-15T11:00:00Z",
             "observed_at": "2026-09-15T10:59:00Z", "raw": {"match_key": "+1 (212) 555-0100"}},
            {"file_id": "near_user_id", "captured_at": "2026-09-15T11:00:00Z",
             "observed_at": "2026-09-15T10:59:00Z", "raw": {"lookup_key": "user_150"}},
            {"file_id": "after_cutoff", "captured_at": "2026-09-15T12:01:00Z",
             "observed_at": "2026-09-15T12:01:00Z", "raw": {"lookup_key": "user_15"}},
        ]
        identifiers = {
            "user_id": {"user_15"}, "email": {"old@example.com"},
            "email_hash": {"hash-15"}, "phone": {"12125550100"}, "name": set(),
        }

        matches = find_matching_evidence(records, identifiers, "2026-09-15T12:00:00Z")

        self.assertEqual({row["file_id"] for row in matches}, {"user", "email", "hash", "phone"})



if __name__ == "__main__":
    unittest.main()
