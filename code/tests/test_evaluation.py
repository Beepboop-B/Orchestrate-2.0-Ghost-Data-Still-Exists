import unittest

from code.evaluation.main import _resource_sources, _step_mismatch_counts


def step(step_no, phase, resource_id, operation, state, evidence_id=""):
    return {
        "step_no": step_no,
        "phase": phase,
        "system_id": "account_service",
        "resource_id": resource_id,
        "operation": operation,
        "state": state,
        "evidence_id": evidence_id,
    }


class EvaluationSourceSummaryTests(unittest.TestCase):
    def test_marks_post_cutoff_evidence_and_activity_as_claim(self):
        evidence = [{
            "resource_id": "account_1", "file_id": "evidence_1",
            "observed_at": "2026-09-01T00:00:00Z",
        }]
        manifest = {"evidence_1": "2026-09-03T00:00:00Z"}
        activities = [{
            "resource_id": "account_1", "activity_id": "activity_1",
            "event_time": "2026-09-01T00:00:00Z", "event_type": "DELETE_RECORD",
            "reported_result": "SUCCESS",
        }]

        summary = _resource_sources(
            "account_1", "2026-09-02T00:00:00Z", evidence, manifest, activities
        )

        self.assertIn("post-audit capture; excluded", summary)
        self.assertIn("activity_1", summary)
        self.assertIn("[claim]", summary)

    def test_reports_when_no_participant_source_mentions_resource(self):
        summary = _resource_sources("account_missing", "2026-09-02T00:00:00Z", [], {}, [])
        self.assertEqual(summary, "no literal resource hit in participant evidence/activity")


class EvaluationMismatchMatrixTests(unittest.TestCase):
    def test_missing_phase_is_not_miscounted_as_missing_resource(self):
        expected = [
            step(1, "FINDING", "account_1", "REPORT_REMAINING_RECORD", "PRESENT", "evidence_1"),
            step(2, "REMEDIATION", "account_1", "DELETE_RECORD", "ABSENT"),
            step(3, "VERIFICATION", "account_1", "VERIFY_RECORD_ABSENT", "ABSENT"),
        ]
        actual = [expected[0], expected[1]]

        counts = _step_mismatch_counts(expected, actual)

        self.assertEqual(counts["missing_resources"], 0)
        self.assertEqual(counts["missing_steps"], 1)
        self.assertEqual(counts["extra_resources"], 0)

    def test_shared_resource_operation_state_and_evidence_differences_are_counted(self):
        expected = [step(1, "VERIFICATION", "account_1", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_1")]
        actual = [step(1, "VERIFICATION", "account_1", "VERIFY_RECORD_PRESENT", "PRESENT", "evidence_2")]

        counts = _step_mismatch_counts(expected, actual)

        self.assertEqual(counts["missing_resources"], 0)
        self.assertEqual(counts["missing_steps"], 0)
        self.assertEqual(counts["operation_or_state_fields"], 2)
        self.assertEqual(counts["wrong_evidence_references"], 1)

    def test_reordering_same_steps_is_reported_as_order_only(self):
        first = step(1, "VERIFICATION", "account_1", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_1")
        second = step(2, "VERIFICATION", "account_2", "VERIFY_RECORD_ABSENT", "ABSENT", "evidence_2")
        actual = [dict(second, step_no=1), dict(first, step_no=2)]

        counts = _step_mismatch_counts([first, second], actual)

        self.assertTrue(counts["ordering_only"])
        self.assertEqual(counts["missing_steps"], 0)
        self.assertEqual(counts["extra_steps"], 0)


if __name__ == "__main__":
    unittest.main()
