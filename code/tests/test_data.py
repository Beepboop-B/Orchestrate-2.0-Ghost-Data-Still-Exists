import unittest
from pathlib import Path

from code.data import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


class DatasetLoadingTests(unittest.TestCase):
    def test_loads_all_participant_inputs_with_expected_request_count(self):
        dataset = load_dataset(REPO_ROOT / "dataset")

        self.assertEqual(len(dataset["requests"]), 518)
        self.assertEqual(len(dataset["identities"]), 850)
        self.assertEqual(len(dataset["audit_log"]), 306)
        self.assertEqual(len(dataset["rules"]), 15)
        self.assertEqual(len(dataset["evidence_manifest"]), 94)
        self.assertEqual(
            dataset["requests"][0]["case_id"], "case_33"
        )


if __name__ == "__main__":
    unittest.main()
