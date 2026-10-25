import unittest

from code.validation import validate_steps


class AdditionalContractScenarios(unittest.TestCase):
    """Participant-authored edge scenarios beyond the public examples."""

    def test_non_deletion_request_has_no_steps(self):
        # A request for a copy/access must not receive deletion actions.
        validate_steps("NOT_APPLICABLE", [])

    def test_incomplete_finding_requires_manifest_evidence(self):
        # An unsupported or absent citation cannot establish a remaining record.
        step = {"step_no": 1, "phase": "FINDING", "system_id": "account_service",
                "resource_id": "account_x", "operation": "REPORT_REMAINING_RECORD",
                "state": "PRESENT", "evidence_id": "evidence_x"}
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            validate_steps("INCOMPLETE", [step], {"evidence_01"})

    def test_complete_requires_only_cited_verification(self):
        # A future remediation plan cannot appear in a completed case.
        step = {"step_no": 1, "phase": "REMEDIATION", "system_id": "account_service",
                "resource_id": "account_x", "operation": "DELETE_RECORD",
                "state": "ABSENT", "evidence_id": ""}
        with self.assertRaisesRegex(ValueError, "COMPLETE may contain only"):
            validate_steps("COMPLETE", [step], {"evidence_01"})

    def test_post_cutoff_evidence_reference_is_rejected(self):
        step = {"step_no": 1, "phase": "VERIFICATION", "system_id": "account_service",
                "resource_id": "account_x", "operation": "VERIFY_RECORD_ABSENT",
                "state": "ABSENT", "evidence_id": "evidence_02"}
        with self.assertRaisesRegex(ValueError, "unavailable at audit_at"):
            validate_steps("COMPLETE", [step], {"evidence_02"}, "2026-09-01T00:00:00Z",
                           {"evidence_02": "2026-09-02T00:00:00Z"})


if __name__ == "__main__":
    unittest.main()
