"""Reconstruct resource state from time-bounded evidence snapshots."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from code.policy import category_for_record


@dataclass(frozen=True)
class EvidenceState:
    state: str
    evidence: Mapping[str, Any]


def _direct_observation(record: Mapping[str, Any], category: str) -> Optional[str]:
    raw = record.get("raw", {})
    # A lookup-started/read-started log line names the resource but says nothing
    # about its state. Its paired completion line carries the actual result.
    if str(raw.get("event", raw.get("event_type", ""))).casefold().endswith("_started"):
        return None
    explicit = str(
        raw.get("state") or raw.get("record_state") or raw.get("result_state") or ""
    ).upper()
    if explicit in {"ABSENT", "NOT_FOUND", "MISSING"}:
        return "ABSENT"
    if explicit in {"PRESENT", "FOUND", "IDENTIFIABLE"}:
        return "PRESENT"
    if explicit in {"REDACTED", "ANONYMIZED"}:
        return explicit
    if explicit in {"ACTIVE", "DISABLED", "BLOCKED"}:
        return explicit

    # A positive direct-identifier scan is an observation of PII still present
    # in the named support/analytics resource, even without a read-completion.
    if (
        str(raw.get("event", raw.get("event_type", ""))).casefold()
        in {"message_pii_scan", "analytics_identity_scan"}
        and raw.get("matched_value")
        and str(raw.get("detector", "")).casefold() == "direct_identifier"
    ):
        return "PRESENT"

    for key in ("status", "status_code", "http_status"):
        value = raw.get(key)
        if str(value) == "404":
            return "ABSENT"
        if str(value) == "200":
            return "PRESENT"

    if category == "DATA_FLOW" and "enabled" in raw:
        enabled = str(raw.get("enabled")).casefold()
        return "ACTIVE" if enabled in {"1", "true", "yes", "active"} else "DISABLED"
    if category == "BACKUP_ARCHIVE" and "restore_allowed" in raw:
        allowed = str(raw.get("restore_allowed")).casefold()
        return "ACTIVE" if allowed in {"1", "true", "yes", "active"} else "BLOCKED"
    if category == "BACKUP_ARCHIVE" and "eligible" in raw:
        eligible = str(raw.get("eligible")).casefold() in {"1", "true", "yes", "eligible"}
        blocked = str(raw.get("deletion_block", "false")).casefold() in {"1", "true", "yes"}
        return "ACTIVE" if eligible and not blocked else "BLOCKED"

    result = str(raw.get("result", "")).casefold()
    if result in {"hit", "found", "present"}:
        return "PRESENT"
    if result in {"not_found", "not found", "miss", "absent"}:
        return "ABSENT"

    for key in ("rows", "total_hits", "total"):
        value = raw.get(key)
        if value is not None:
            try:
                count = int(value)
            except (TypeError, ValueError):
                continue
            if count == 0:
                return "ABSENT"
            if count > 0:
                return "PRESENT"

    event = str(raw.get("event", raw.get("event_type", ""))).casefold()
    if event.endswith("_completed") and any(
        raw.get(key) not in (None, "") and str(raw.get(key)).strip().casefold() not in {"null", "none"}
        for key in (
            "email", "owner_email", "customer_email", "requester_email",
            "phone", "owner_phone", "requester_phone", "email_hash",
            "customer_reference", "subject_reference", "user_id",
        )
    ):
        return "PRESENT"

    if record.get("resource_id") and not any(
        key in raw for key in ("event", "event_type", "level", "trace_id", "request_id")
    ):
        return "PRESENT"
    return None


def _is_matching_scope(
    record: Mapping[str, Any], system_id: str, data_category: str,
    resource_collection: Optional[str] = None,
) -> bool:
    raw = record.get("raw", {})
    if not raw.get("scope") or record.get("system_id") != system_id:
        return False
    scope_category = category_for_record(
        str(raw.get("scope_system") or system_id),
        str(raw.get("scope_collection") or record.get("collection", "")),
        raw,
    )
    if scope_category != data_category:
        return False
    scope_collection = str(raw.get("scope_collection") or record.get("collection", ""))
    # A generic inventory scope does not establish absence from a separately
    # named replica (for example, primary vs failover profile tables).
    if resource_collection and scope_collection:
        replica_markers = ("primary", "replica", "failover", "regional")
        if any(marker in resource_collection.casefold() for marker in replica_markers):
            return scope_collection.casefold() == resource_collection.casefold()
    return True


def reconstruct_resource_state(
    records: Iterable[Mapping[str, Any]],
    resource_id: str,
    system_id: str,
    data_category: str,
    audit_at: str,
    resource_collection: Optional[str] = None,
) -> Optional[EvidenceState]:
    """Return the latest evidenced state for one resource at an audit cutoff.

    A current row wins over an equally timed scope marker, which is important
    when a failover replica still contains data absent from the primary.
    """
    candidates = []
    for record in records:
        # The outer evidence capture is an availability bound; an inner source
        # timestamp cannot make a later-exported file eligible retroactively.
        captured = str(record.get("captured_at") or "")
        observed = str(record.get("observed_at") or captured)
        if not captured or captured > audit_at or observed > audit_at:
            continue
        if record.get("resource_id") == resource_id and record.get("system_id") == system_id:
            category = category_for_record(
                system_id, str(record.get("collection", "")), record.get("raw", {})
            )
            if category != data_category:
                continue
            state = _direct_observation(record, data_category)
            if state:
                rank = 2 if state not in {"ABSENT"} else 1
                candidates.append((observed, rank, dict(record), state))
        elif _is_matching_scope(record, system_id, data_category, resource_collection):
            candidates.append((observed, 0, dict(record), "ABSENT"))

    if not candidates:
        return None
    observed, _, evidence, state = max(candidates, key=lambda item: (item[0], item[1], item[2].get("file_id", "")))
    return EvidenceState(state=state, evidence=evidence)
