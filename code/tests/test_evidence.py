import unittest
from pathlib import Path

from code.evidence import _parse_text_records, load_evidence_files, parse_evidence_file
from code.data import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "dataset"


class EvidenceParserTests(unittest.TestCase):
    def test_reads_nested_json_snapshot_records_with_system_and_provenance(self):
        records = parse_evidence_file(
            DATASET
            / "evidence/records/customer_data_snapshot_bundle_20260915.json",
            "evidence_51",
            "2026-09-15T12:00:00Z",
        )

        tombstone = next(r for r in records if r.get("resource_id") == "tombstone_440")
        self.assertEqual(tombstone["system_id"], "identity_service")
        self.assertEqual(tombstone["file_id"], "evidence_51")
        self.assertEqual(tombstone["observed_at"], "2026-09-15T12:00:00Z")
        self.assertEqual(tombstone["raw"]["subject_reference"], "user_541")

    def test_reads_sql_snapshot_rows_with_their_table_and_source(self):
        records = parse_evidence_file(
            DATASET
            / "evidence/databases/customer_accounts_failover_replica_20260902.sql",
            "evidence_54",
            "2026-09-02T23:00:00Z",
        )

        profile = next(r for r in records if r.get("resource_id") == "account_005")
        self.assertEqual(profile["file_id"], "evidence_54")
        self.assertIn("customer_profiles", profile["collection"])
        self.assertEqual(profile["observed_at"], "2026-09-02T23:00:00Z")

    def test_infers_search_service_for_primary_search_table(self):
        records = parse_evidence_file(
            DATASET / "evidence/databases/customer_search_primary_20260910.sql",
            "evidence_57",
            "2026-09-10T08:45:00Z",
        )
        search = next(r for r in records if r.get("resource_id") == "search_001")
        self.assertEqual(search["system_id"], "search_service")

    def test_propagates_trace_identity_to_non_completion_resource_events(self):
        records = parse_evidence_file(
            DATASET / "evidence/logs/service_events_ap_south_20260915.log",
            "evidence_01", "2026-09-15T11:59:39Z",
        )
        flow = next(r for r in records if r.get("resource_id") == "data_flow_9846")
        backup = next(r for r in records if r.get("resource_id") == "backup_3245")
        self.assertEqual(flow["raw"].get("subject_key"), "lucia-torres@gmail.com")
        self.assertEqual(backup["raw"].get("subject_key"), "leonie.g9352@outlook.com")

    def test_extracts_text_from_ascii85_flate_pdf_evidence(self):
        records = parse_evidence_file(
            DATASET / "evidence/documents/delivery_correction_attachment.pdf",
            "evidence_58",
            "2026-09-12T07:30:00Z",
        )

        self.assertEqual(len(records), 1)
        self.assertIn("support_001", records[0]["text"])
        self.assertIn("Priya Raman", records[0]["text"])
        self.assertEqual(records[0]["file_id"], "evidence_58")

    def test_parses_handover_rows_as_individual_time_bounded_facts(self):
        records = parse_evidence_file(
            DATASET / "evidence/records/customer_account_handover_20261001.txt",
            "evidence_03",
            "2026-10-01T12:00:00Z",
        )

        flow = next(r for r in records if r.get("resource_id") == "data_flow_9522")
        self.assertEqual(flow["system_id"], "integration_service")
        self.assertEqual(flow["raw"]["state"], "ACTIVE")
        self.assertEqual(flow["raw"]["subject_reference"], "novak.tomasz@icloud.com")

    def test_parses_structured_log_attributes_for_a_resource_lookup(self):
        records = parse_evidence_file(
            DATASET / "evidence/logs/resource_lookup_trace_20260926_103856.log",
            "evidence_94",
            "2026-09-26T10:38:56Z",
        )

        lookup = next(
            r
            for r in records
            if r.get("resource_id") == "search_4262"
            and r["raw"].get("event") == "index_query_completed"
        )
        self.assertEqual(lookup["system_id"], "search_service")
        self.assertEqual(lookup["raw"]["result"], "hit")
        self.assertEqual(lookup["raw"]["total_hits"], "1")

    def test_parses_timestamped_json_log_events_and_correlates_start_identity(self):
        text = (
            '2026-09-16T08:52:49Z {"service":"security_service","trace_id":"tr-1",'
            '"event":"audit_record_query_started","subject_ref":"user_61"}\n'
            '2026-09-16T08:52:59Z {"service":"security_service","trace_id":"tr-1",'
            '"resource_id":"audit_record_4902","event":"audit_record_read_completed",'
            '"integrity_check":"passed","rows":"1"}\n'
        )
        records = _parse_text_records(
            Path("structured.log"), "evidence_6", "2026-09-18T11:55:24Z", text
        )

        result = next(row for row in records if row.get("resource_id") == "audit_record_4902")
        self.assertEqual(result["system_id"], "security_service")
        self.assertEqual(result["observed_at"], "2026-09-16T08:52:59Z")
        self.assertEqual(result["raw"].get("subject_ref"), "user_61")

    def test_loads_every_manifest_file_without_losing_provenance(self):
        dataset = load_dataset(DATASET)
        records = load_evidence_files(DATASET, dataset["evidence_manifest"])

        self.assertEqual({r["file_id"] for r in records}, {
            f"evidence_{number:02d}" for number in range(1, 95)
        })
        self.assertTrue(all(r["captured_at"] and r["source_path"] for r in records))


if __name__ == "__main__":
    unittest.main()
