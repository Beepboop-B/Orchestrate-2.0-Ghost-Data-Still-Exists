"""Temporal eligibility tests for nested snapshots in later evidence bundles."""

import unittest
from pathlib import Path

from code.audit import find_matching_evidence
from code.evidence import _parse_json
from code.state import reconstruct_resource_state


class NestedSnapshotTemporalTests(unittest.TestCase):
    audit_at = "2026-09-15T12:00:00Z"
    identifiers = {
        "user_id": {"user_1"},
        "email": {"person@example.com"},
        "phone": set(),
        "email_hash": set(),
        "name": set(),
    }

    def _parse_bundle(self, manifest_capture, snapshot_capture):
        bundle = {
            "exported_at": manifest_capture,
            "snapshots": [{
                "captured_at": snapshot_capture,
                "data_store": "account_service",
                "collection": "customer_profiles",
                "records": [{
                    "resource_id": "account_1",
                    "customer_reference": "user_1",
                    "email": "person@example.com",
                }],
            }],
        }
        return _parse_json(bundle, "evidence_bundle", Path("bundle.json"), manifest_capture)

    def test_snapshot_and_manifest_at_exact_cutoff_are_eligible(self):
        records = self._parse_bundle(self.audit_at, self.audit_at)

        self.assertEqual(records[0]["captured_at"], self.audit_at)
        self.assertEqual(records[0]["observed_at"], self.audit_at)
        self.assertEqual(
            find_matching_evidence(records, self.identifiers, self.audit_at), records
        )
        state = reconstruct_resource_state(
            records, "account_1", "account_service", "USER_PROFILE", self.audit_at
        )
        self.assertEqual(state.state, "PRESENT")

    def test_earlier_nested_snapshot_in_later_export_is_not_available_at_cutoff(self):
        records = self._parse_bundle(
            "2026-09-17T12:00:00Z", "2026-09-09T12:00:00Z"
        )

        self.assertEqual(records[0]["captured_at"], "2026-09-17T12:00:00Z")
        self.assertEqual(records[0]["observed_at"], "2026-09-09T12:00:00Z")
        self.assertEqual(find_matching_evidence(records, self.identifiers, self.audit_at), [])
        self.assertIsNone(reconstruct_resource_state(
            records, "account_1", "account_service", "USER_PROFILE", self.audit_at
        ))

    def test_nested_snapshot_after_cutoff_is_rejected_even_if_file_is_available(self):
        records = self._parse_bundle(
            "2026-09-15T11:00:00Z", "2026-09-15T12:00:01Z"
        )

        self.assertEqual(find_matching_evidence(records, self.identifiers, self.audit_at), [])
        self.assertIsNone(reconstruct_resource_state(
            records, "account_1", "account_service", "USER_PROFILE", self.audit_at
        ))


if __name__ == "__main__":
    unittest.main()
