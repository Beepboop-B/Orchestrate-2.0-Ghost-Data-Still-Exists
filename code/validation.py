"""Output contract validation shared by prediction and evaluation commands."""

import csv
import json
from pathlib import Path
from typing import Iterable, Mapping

from code.planner import OPERATION_ORDER, OPERATION_STATES


OUTPUT_COLUMNS = ("case_id", "deletion_status", "steps_json")
VALID_STATUSES = {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}


def validate_steps(
    status: str,
    steps: object,
    valid_evidence_ids: set[str] | None = None,
    audit_at: str | None = None,
    evidence_captured_at: Mapping[str, str] | None = None,
) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid deletion status: {status}")
    if not isinstance(steps, list):
        raise ValueError("steps_json must decode to an array")
    if status == "NOT_APPLICABLE" and steps:
        raise ValueError("NOT_APPLICABLE must use an empty steps array")
    phases = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
    last_phase = -1
    last_key = None
    for index, step in enumerate(steps, 1):
        fields = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}
        if not isinstance(step, dict) or set(step) != fields:
            raise ValueError(f"step {index} must contain exactly {sorted(fields)}")
        if step["step_no"] != index:
            raise ValueError(f"step numbering is not consecutive at index {index}")
        phase = step["phase"]
        if phase not in phases or phases[phase] < last_phase:
            raise ValueError(f"invalid phase order at step {index}")
        last_phase = phases[phase]
        order = OPERATION_ORDER.get(phase, [])
        operation = step["operation"]
        if operation not in order or OPERATION_STATES.get(operation) != step["state"]:
            raise ValueError(f"unsupported operation/state at step {index}")
        key = (phases[phase], order.index(operation), step["system_id"], step["resource_id"])
        if last_key is not None and key < last_key:
            raise ValueError(f"step ordering violation at index {index}")
        last_key = key
        evidence_id = step["evidence_id"]
        if phase == "FINDING" or (status == "COMPLETE" and phase == "VERIFICATION"):
            if not evidence_id:
                raise ValueError(f"step {index} requires evidence")
            if valid_evidence_ids is not None and evidence_id not in valid_evidence_ids:
                raise ValueError(f"step {index} cites unknown evidence {evidence_id}")
            if audit_at and evidence_captured_at is not None:
                captured_at = evidence_captured_at.get(evidence_id)
                if captured_at is None or captured_at > audit_at:
                    raise ValueError(f"step {index} cites evidence unavailable at audit_at")
        elif evidence_id:
            raise ValueError(f"step {index} must not cite evidence")
        if status == "COMPLETE" and phase != "VERIFICATION":
            raise ValueError("COMPLETE may contain only verification steps")


def read_output(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != OUTPUT_COLUMNS:
            raise ValueError(f"output header must be {','.join(OUTPUT_COLUMNS)}")
        rows = list(reader)
    if any(None in row for row in rows):
        raise ValueError("output row has extra columns")
    return rows


def validate_output_rows(
    rows: Iterable[Mapping[str, str]],
    expected_case_ids: list[str],
    valid_evidence_ids: set[str] | None = None,
    audit_cutoffs: Mapping[str, str] | None = None,
    evidence_captured_at: Mapping[str, str] | None = None,
) -> None:
    rows = list(rows)
    ids = [row["case_id"] for row in rows]
    if ids != sorted(expected_case_ids) or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("output case IDs must be unique and sorted")
    if set(ids) != set(expected_case_ids) or len(ids) != len(expected_case_ids):
        raise ValueError(f"expected {len(expected_case_ids)} rows, found {len(ids)}")
    for row in rows:
        steps = json.loads(row["steps_json"])
        validate_steps(
            row["deletion_status"], steps, valid_evidence_ids,
            (audit_cutoffs or {}).get(row["case_id"]), evidence_captured_at,
        )


def serialize_rows(predictions: Iterable[Mapping[str, object]]) -> list[dict[str, str]]:
    rows = []
    for prediction in predictions:
        status = str(prediction["deletion_status"])
        steps = prediction["steps"]
        validate_steps(status, steps)
        rows.append({
            "case_id": str(prediction["case_id"]),
            "deletion_status": status,
            "steps_json": json.dumps(steps, ensure_ascii=False, separators=(",", ":")),
        })
    return sorted(rows, key=lambda row: row["case_id"])
