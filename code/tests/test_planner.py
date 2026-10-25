import unittest

from code.planner import build_steps


class StepPlanningTests(unittest.TestCase):
    def test_orders_operations_by_contract_then_system_and_resource(self):
        findings = [
            {"system_id": "integration_service", "resource_id": "data_flow_2", "operation": "REPORT_ACTIVE_DATA_FLOW", "state": "ACTIVE", "evidence_id": "evidence_1"},
            {"system_id": "support_platform", "resource_id": "support_2", "operation": "REPORT_EXPOSED_PII", "state": "PRESENT", "evidence_id": "evidence_1"},
            {"system_id": "search_service", "resource_id": "search_1", "operation": "REPORT_REMAINING_RECORD", "state": "PRESENT", "evidence_id": "evidence_1"},
        ]
        remediation = [
            {"system_id": "search_service", "resource_id": "search_1", "operation": "DELETE_RECORD", "state": "ABSENT"},
            {"system_id": "integration_service", "resource_id": "data_flow_2", "operation": "DISABLE_DATA_FLOW", "state": "DISABLED"},
        ]
        verification = [
            {"system_id": "support_platform", "resource_id": "support_2", "operation": "VERIFY_RECORD_REDACTED", "state": "REDACTED"},
            {"system_id": "search_service", "resource_id": "search_1", "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT"},
            {"system_id": "integration_service", "resource_id": "data_flow_2", "operation": "VERIFY_DATA_FLOW_DISABLED", "state": "DISABLED"},
        ]

        steps = build_steps("INCOMPLETE", findings, remediation, verification)

        self.assertEqual(
            [(s["phase"], s["operation"]) for s in steps],
            [
                ("FINDING", "REPORT_REMAINING_RECORD"),
                ("FINDING", "REPORT_EXPOSED_PII"),
                ("FINDING", "REPORT_ACTIVE_DATA_FLOW"),
                ("REMEDIATION", "DISABLE_DATA_FLOW"),
                ("REMEDIATION", "DELETE_RECORD"),
                ("VERIFICATION", "VERIFY_RECORD_ABSENT"),
                ("VERIFICATION", "VERIFY_RECORD_REDACTED"),
                ("VERIFICATION", "VERIFY_DATA_FLOW_DISABLED"),
            ],
        )
        self.assertEqual([s["step_no"] for s in steps], list(range(1, 9)))
        self.assertEqual(steps[0]["evidence_id"], "evidence_1")
        self.assertEqual(steps[-1]["evidence_id"], "")

    def test_not_applicable_has_no_steps(self):
        self.assertEqual(build_steps("NOT_APPLICABLE", [], [], []), [])

    def test_complete_contains_only_evidence_backed_verification_steps(self):
        steps = build_steps(
            "COMPLETE",
            [],
            [],
            [{"system_id": "account_service", "resource_id": "account_1", "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT", "evidence_id": "evidence_1"}],
        )

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["phase"], "VERIFICATION")
        self.assertEqual(steps[0]["evidence_id"], "evidence_1")


if __name__ == "__main__":
    unittest.main()
