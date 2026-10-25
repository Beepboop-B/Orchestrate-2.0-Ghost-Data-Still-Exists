"""Deterministic end-to-end deletion audit engine."""

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from code.audit import find_account_resource_hint, find_matching_evidence
from code.authorization import authorizes_deletion
from code.identity import identifiers_for_user, resolve_email
from code.planner import build_steps
from code.policy import category_for_record, evaluate_record
from code.state import reconstruct_resource_state


def _sort(items: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (dict(item) for item in items),
        key=lambda item: (item["system_id"], item["resource_id"]),
    )


def audit_request(request: Mapping[str, str], dataset: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Audit one request using only participant-facing records and cutoff-safe evidence."""
    if not authorizes_deletion(request.get("request_text", "")):
        return {"case_id": request["case_id"], "deletion_status": "NOT_APPLICABLE", "steps": []}

    user_id = resolve_email(
        request.get("email", ""), dataset["identities"], dataset["audit_log"], request["audit_at"]
    )
    if not user_id:
        return {
            "case_id": request["case_id"],
            "deletion_status": "INCOMPLETE",
            "steps": [],
        }

    identifiers = identifiers_for_user(
        user_id, dataset["identities"], dataset["audit_log"], request["audit_at"]
    )
    linked = find_matching_evidence(evidence, identifiers, request["audit_at"])
    candidates: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for record in linked:
        resource_id = record.get("resource_id")
        system_id = record.get("system_id")
        if not resource_id or not system_id:
            continue
        # A historical account lookup can identify a resource that was empty
        # months before the request. It cannot establish that this resource
        # still belongs to the requester after a later deletion request.
        if system_id == "account_service":
            linked_observed_at = str(record.get("observed_at") or record.get("captured_at") or "")
            if linked_observed_at < request.get("requested_at", ""):
                continue
        category = category_for_record(system_id, str(record.get("collection", "")), record.get("raw", {}))
        if category:
            key = (system_id, resource_id, category)
            prior = candidates.get(key)
            # Prefer a structured resource snapshot over a log line or handover
            # summary when both identify the same resource.
            if prior is None or (prior.get("collection") in {"", "text_log"} and record.get("collection") not in {"", "text_log"}):
                candidates[key] = record

    # An operational deletion event may identify a workflow resource only
    # under a unique request/event correlation. It never proves the resource's
    # state; an eligible evidence observation must establish that separately.
    if not any(system_id == "account_service" for system_id, _rid, _category in candidates):
        request_universe = dataset.get("request_universe", [request])
        account_hint = dataset.get("account_link_hints", {}).get(request["case_id"])
        if account_hint is None:
            # Retain the previously integrated uniquely correlated rule as a
            # fallback; the status-consistent propagation is additive.
            account_hint = find_account_resource_hint(
                request, dataset.get("activities", []), request_universe
            )
        if account_hint:
            resource_id, _activity_id = account_hint
            account_state = reconstruct_resource_state(
                evidence, resource_id, "account_service", "USER_PROFILE",
                request["audit_at"],
            )
            if account_state and account_state.state == "ABSENT":
                candidates.setdefault(
                    ("account_service", resource_id, "USER_PROFILE"), {}
                )

    findings: List[Dict[str, Any]] = []
    remediation: List[Dict[str, Any]] = []
    verification: List[Dict[str, Any]] = []
    all_compliant = True
    established_any_state = False

    for (system_id, resource_id, category), _linked_record in sorted(candidates.items()):
        current = reconstruct_resource_state(
            evidence, resource_id, system_id, category, request["audit_at"],
            str(_linked_record.get("collection") or "") or None,
        )
        if current is None:
            all_compliant = False
            continue
        # Evidence captured before the person submitted the deletion request is
        # useful historical context, but it cannot verify post-request state.
        if str(current.evidence.get("captured_at") or "") < request.get("requested_at", ""):
            all_compliant = False
            continue
        established_any_state = True
        raw = current.evidence.get("raw", {})
        policy = evaluate_record(category, raw, user_id, request["audit_at"], dataset["rules"], identifiers)
        source_id = current.evidence.get("file_id", "")

        # Absence from a scoped snapshot is compliant only for delete categories.
        if current.state == "ABSENT":
            action = policy.required_action
            if action in {"REDACT", "ANONYMIZE", "RETAIN"}:
                all_compliant = False
            else:
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT",
                                     "evidence_id": source_id})
            continue

        if category == "DATA_FLOW":
            active = policy.violation
            if active:
                all_compliant = False
                findings.append({"system_id": system_id, "resource_id": resource_id,
                                 "operation": "REPORT_ACTIVE_DATA_FLOW", "state": "ACTIVE",
                                 "evidence_id": source_id})
                remediation.append({"system_id": system_id, "resource_id": resource_id,
                                    "operation": "DISABLE_DATA_FLOW", "state": "DISABLED"})
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_DATA_FLOW_DISABLED", "state": "DISABLED"})
            else:
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_DATA_FLOW_DISABLED", "state": "DISABLED",
                                     "evidence_id": source_id})
            continue

        if category == "BACKUP_ARCHIVE":
            if policy.violation:
                all_compliant = False
                findings.append({"system_id": system_id, "resource_id": resource_id,
                                 "operation": "REPORT_RESTORE_RISK", "state": "ACTIVE",
                                 "evidence_id": source_id})
                remediation.append({"system_id": system_id, "resource_id": resource_id,
                                    "operation": "BLOCK_RESTORE", "state": "BLOCKED"})
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_RESTORE_BLOCKED", "state": "BLOCKED"})
            else:
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_RESTORE_BLOCKED", "state": "BLOCKED",
                                     "evidence_id": source_id})
            continue

        action = policy.required_action
        if action == "RETAIN":
            if policy.violation:
                all_compliant = False
                findings.append({"system_id": system_id, "resource_id": resource_id,
                                 "operation": "REPORT_EXPOSED_PII", "state": "PRESENT",
                                 "evidence_id": source_id})
                remediation.append({"system_id": system_id, "resource_id": resource_id,
                                    "operation": "REDACT_RECORD", "state": "REDACTED"})
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_RECORD_REDACTED", "state": "REDACTED"})
            else:
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": "VERIFY_RECORD_PRESENT", "state": "PRESENT",
                                     "evidence_id": source_id})
        elif action in {"REDACT", "ANONYMIZE"}:
            if policy.violation:
                all_compliant = False
                findings.append({"system_id": system_id, "resource_id": resource_id,
                                 "operation": "REPORT_EXPOSED_PII", "state": "PRESENT",
                                 "evidence_id": source_id})
                op = "REDACT_RECORD" if action == "REDACT" else "ANONYMIZE_RECORD"
                vop = "VERIFY_RECORD_REDACTED" if action == "REDACT" else "VERIFY_RECORD_ANONYMIZED"
                expected = "REDACTED" if action == "REDACT" else "ANONYMIZED"
                remediation.append({"system_id": system_id, "resource_id": resource_id,
                                    "operation": op, "state": expected})
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": vop, "state": expected})
            else:
                vop = "VERIFY_RECORD_REDACTED" if action == "REDACT" else "VERIFY_RECORD_ANONYMIZED"
                expected = "REDACTED" if action == "REDACT" else "ANONYMIZED"
                verification.append({"system_id": system_id, "resource_id": resource_id,
                                     "operation": vop, "state": expected,
                                     "evidence_id": source_id})
        elif action == "DELETE":
            all_compliant = False
            findings.append({"system_id": system_id, "resource_id": resource_id,
                             "operation": "REPORT_REMAINING_RECORD", "state": "PRESENT",
                             "evidence_id": source_id})
            remediation.append({"system_id": system_id, "resource_id": resource_id,
                                "operation": "DELETE_RECORD", "state": "ABSENT"})
            verification.append({"system_id": system_id, "resource_id": resource_id,
                                 "operation": "VERIFY_RECORD_ABSENT", "state": "ABSENT"})

    # A linked account state must be established before a deletion can be declared complete.
    if not established_any_state:
        all_compliant = False
    status = "COMPLETE" if all_compliant else "INCOMPLETE"
    if status == "INCOMPLETE" and not findings:
        # Unknown identity/state is not evidence of a violation; return no unsupported claim.
        steps = []
    else:
        if status == "INCOMPLETE":
            # Every verification in an incomplete plan is a required future check.
            for item in verification:
                item["evidence_id"] = ""
        steps = build_steps(status, findings, remediation, verification)
    return {"case_id": request["case_id"], "deletion_status": status, "steps": steps}
