"""Deterministic construction and validation of contract step arrays."""

from typing import Any, Dict, Iterable, List, Mapping


OPERATION_ORDER = {
    "FINDING": [
        "REPORT_REMAINING_RECORD",
        "REPORT_EXPOSED_PII",
        "REPORT_ACTIVE_DATA_FLOW",
        "REPORT_RESTORE_RISK",
    ],
    "REMEDIATION": [
        "DISABLE_DATA_FLOW",
        "BLOCK_RESTORE",
        "DELETE_RECORD",
        "REDACT_RECORD",
        "ANONYMIZE_RECORD",
    ],
    "VERIFICATION": [
        "VERIFY_RECORD_ABSENT",
        "VERIFY_RECORD_PRESENT",
        "VERIFY_RECORD_REDACTED",
        "VERIFY_RECORD_ANONYMIZED",
        "VERIFY_DATA_FLOW_DISABLED",
        "VERIFY_RESTORE_BLOCKED",
    ],
}

OPERATION_STATES = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}


def _sort_key(phase: str, item: Mapping[str, Any]) -> tuple:
    operation_order = OPERATION_ORDER[phase].index(item["operation"])
    return (
        operation_order,
        item["system_id"],
        item["resource_id"],
        item.get("evidence_id", ""),
    )


def _validate_item(phase: str, item: Mapping[str, Any], status: str) -> None:
    operation = item["operation"]
    if operation not in OPERATION_ORDER[phase]:
        raise ValueError(f"Operation {operation!r} is not allowed in {phase}")
    if item["state"] != OPERATION_STATES[operation]:
        raise ValueError(f"Invalid state {item['state']!r} for {operation}")
    evidence_id = item.get("evidence_id", "")
    if phase == "FINDING" or status == "COMPLETE":
        if not evidence_id:
            raise ValueError(f"{phase} evidence must cite a participant-facing source")
    elif evidence_id:
        raise ValueError("Planned remediation and future verification must have empty evidence")


def build_steps(
    status: str,
    findings: Iterable[Mapping[str, Any]],
    remediation: Iterable[Mapping[str, Any]],
    verification: Iterable[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a contract-compliant, consecutively numbered ordered step list."""
    if status not in {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"}:
        raise ValueError(f"Invalid deletion status: {status}")
    if status == "NOT_APPLICABLE":
        if list(findings) or list(remediation) or list(verification):
            raise ValueError("NOT_APPLICABLE cases must have no steps")
        return []

    phase_items = {
        "FINDING": list(findings) if status == "INCOMPLETE" else [],
        "REMEDIATION": list(remediation) if status == "INCOMPLETE" else [],
        "VERIFICATION": list(verification),
    }
    result = []
    for phase in ("FINDING", "REMEDIATION", "VERIFICATION"):
        items = sorted(phase_items[phase], key=lambda item: _sort_key(phase, item))
        seen = set()
        for item in items:
            _validate_item(phase, item, status)
            identity = (
                phase,
                item["system_id"],
                item["resource_id"],
                item["operation"],
                item["state"],
                item.get("evidence_id", ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            evidence_id = item.get("evidence_id", "")
            result.append(
                {
                    "step_no": len(result) + 1,
                    "phase": phase,
                    "system_id": item["system_id"],
                    "resource_id": item["resource_id"],
                    "operation": item["operation"],
                    "state": item["state"],
                    "evidence_id": evidence_id,
                }
            )
    return result
