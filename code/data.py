"""Participant-facing CSV loading and schema checks."""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence


SCHEMAS = {
    "deletion_requests.csv": (
        "case_id", "email", "requested_at", "reported_status", "reported_at",
        "audit_at", "request_text",
    ),
    "sample_deletion_requests.csv": (
        "case_id", "email", "requested_at", "reported_status", "reported_at",
        "audit_at", "request_text",
    ),
    "user_identities.csv": (
        "user_id", "name", "email", "phone", "email_hash", "updated_at",
    ),
    "user_audit_log.csv": (
        "audit_id", "user_id", "event_time", "field_name", "old_value", "new_value",
    ),
    "system_activity.csv": (
        "activity_id", "event_time", "event_type", "source_system", "target_system",
        "resource_id", "reported_result", "details",
    ),
    "deletion_rules.csv": ("rule_id", "data_category", "condition", "required_action"),
    "evidence_files.csv": ("file_id", "file_path", "origin", "captured_at"),
}


def load_csv(path: Path, required_columns: Optional[Sequence[str]] = None) -> List[Dict[str, str]]:
    """Read a UTF-8 CSV and reject a schema that differs from its contract."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        if required_columns is not None and tuple(reader.fieldnames) != tuple(required_columns):
            raise ValueError(
                f"Unexpected columns in {path}: {reader.fieldnames!r}; "
                f"expected {list(required_columns)!r}"
            )
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError(f"CSV row has more fields than its header: {path}")
    return rows


def load_dataset(dataset_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    """Load only the participant-facing inputs used to create predictions.

    Public sample labels are deliberately excluded from this prediction input.
    """
    root = Path(dataset_dir)
    names = {
        "requests": "deletion_requests.csv",
        "sample_requests": "sample_deletion_requests.csv",
        "identities": "user_identities.csv",
        "audit_log": "user_audit_log.csv",
        "activities": "system_activity.csv",
        "rules": "deletion_rules.csv",
        "evidence_manifest": "evidence_files.csv",
    }
    return {
        key: load_csv(root / filename, SCHEMAS[filename])
        for key, filename in names.items()
    }
