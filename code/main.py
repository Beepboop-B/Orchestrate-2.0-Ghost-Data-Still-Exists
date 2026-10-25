"""Generate auditable deletion predictions from participant-facing data."""

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from code.data import load_dataset
from code.audit import find_exact_account_owners, find_status_consistent_account_hints
from code.engine import audit_request
from code.evidence import load_evidence_files
from code.validation import OUTPUT_COLUMNS, serialize_rows, validate_output_rows


def predict(dataset_dir: Path, requests_key: str = "requests"):
    dataset = load_dataset(dataset_dir)
    evidence = load_evidence_files(dataset_dir, dataset["evidence_manifest"])
    # Use the complete request universe for one-to-one event propagation for
    # both full and sample predictions.
    dataset["request_universe"] = list(dataset["requests"]) + list(dataset["sample_requests"])
    exact_account_owners = find_exact_account_owners(
        evidence, dataset["request_universe"], dataset["identities"], dataset["audit_log"]
    )
    dataset["account_link_hints"] = find_status_consistent_account_hints(
        dataset["activities"], dataset["request_universe"], exact_account_owners
    )
    evidence_ids = {item["file_id"] for item in dataset["evidence_manifest"]}
    evidence_captured_at = {item["file_id"]: item["captured_at"] for item in dataset["evidence_manifest"]}
    predictions = [audit_request(request, dataset, evidence) for request in dataset[requests_key]]
    rows = serialize_rows(predictions)
    expected = sorted(row["case_id"] for row in dataset[requests_key])
    validate_output_rows(
        rows, expected, evidence_ids,
        {row["case_id"]: row["audit_at"] for row in dataset[requests_key]},
        evidence_captured_at,
    )
    return rows


def write_csv(path: Path, rows) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", action="store_true", help="generate predictions for public requests only")
    parser.add_argument("--output", type=Path, help="output CSV path (defaults to repository output.csv for full run)")
    args = parser.parse_args(argv)
    dataset_dir = REPO_ROOT / "dataset"
    rows = predict(dataset_dir, "sample_requests" if args.samples else "requests")
    target = args.output or (REPO_ROOT / "code" / "evaluation" / "sample_predictions.csv" if args.samples else REPO_ROOT / "output.csv")
    expected_count = 32 if args.samples else 518
    if len(rows) != expected_count:
        raise ValueError(f"Expected {expected_count} rows, got {len(rows)}")
    write_csv(target, rows)
    print(f"Wrote {len(rows)} validated rows to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
