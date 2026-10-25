"""Deletion-policy interpretation for evidence-backed resource records."""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional


KNOWN_CATEGORIES = {
    "USER_PROFILE", "SECONDARY_IDENTIFIER", "SEARCH_INDEX_ENTRY", "CACHE_ENTRY",
    "SUPPORT_MESSAGE", "SUPPORT_ATTACHMENT", "ANALYTICS_PROFILE",
    "PRODUCT_TELEMETRY", "USER_EXPORT", "MARKETING_PROFILE",
    "EMAIL_DELIVERY_LOG", "SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD",
    "BACKUP_ARCHIVE", "ACCOUNT_TOMBSTONE",
}


def category_for_record(system_id: str, collection: str, raw: Mapping[str, Any]) -> str:
    """Map participant-facing resource metadata to a policy category."""
    explicit = str(raw.get("data_category") or raw.get("record_type") or "").upper()
    if explicit in KNOWN_CATEGORIES:
        return explicit
    if any(key.casefold() in {"email_opt_in", "marketing_opt_in", "marketing_consent"} for key in raw):
        return "MARKETING_PROFILE"
    system = str(system_id or raw.get("service") or "").casefold()
    source = str(collection or "").casefold()
    combined = f"{system} {source} {raw.get('resource_id', '')}".casefold()

    if "attachment" in combined:
        return "SUPPORT_ATTACHMENT"
    if "tombstone" in combined or "identity_service" in system or "deleted_customer_references" in source:
        return "ACCOUNT_TOMBSTONE"
    if "email_delivery" in combined or "notification_service" in system:
        return "EMAIL_DELIVERY_LOG"
    if "legal" in system or "legal_hold" in combined or "retained_order" in source:
        return "LEGAL_HOLD_RECORD"
    if "backup" in system or "backup_" in combined or "restore_entries" in source:
        return "BACKUP_ARCHIVE"
    if "integration" in system or "connector" in source or "data_flow" in combined:
        return "DATA_FLOW"
    if "cache" in system or "cache" in source:
        return "CACHE_ENTRY"
    if "search" in system or "search" in source or "search_" in combined:
        return "SEARCH_INDEX_ENTRY"
    if "analytics" in system or "analytics" in source:
        return "ANALYTICS_PROFILE"
    if "telemetry" in source:
        return "PRODUCT_TELEMETRY"
    if "support" in system or "support" in source:
        return "SUPPORT_MESSAGE"
    if "export" in system or "export" in source or "export_" in combined:
        return "USER_EXPORT"
    if "marketing" in system or "marketing" in source:
        return "MARKETING_PROFILE"
    if "security" in system or "security" in source or "audit_record_" in combined:
        return "SECURITY_AUDIT_LOG"
    if "account" in system or "customer_profile" in source or "account_" in combined:
        return "USER_PROFILE"
    return ""


@dataclass(frozen=True)
class PolicyResult:
    required_action: Optional[str]
    state: str
    violation: bool


def _values(raw: Any, keys: set[str]) -> list[Any]:
    found = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key.casefold() in keys and value not in (None, "") and str(value).strip().casefold() not in {"null", "none"}:
                found.append(value)
            found.extend(_values(value, keys))
    elif isinstance(raw, list):
        for value in raw:
            found.extend(_values(value, keys))
    return found


def _rule_actions(rules: Iterable[Mapping[str, str]]) -> Dict[str, str]:
    return {
        row["data_category"].upper(): row["required_action"].upper()
        for row in rules
    }


def evaluate_record(
    data_category: str,
    raw: Mapping[str, Any],
    subject_id: str,
    audit_at: str,
    rules: Iterable[Mapping[str, str]],
    subject_identifiers: Optional[Mapping[str, set[str]]] = None,
) -> PolicyResult:
    """Evaluate the current treatment required for a present evidence record."""
    category = (data_category or "").upper()
    action = _rule_actions(rules).get(category)

    if category == "DATA_FLOW":
        enabled = raw.get("enabled")
        active = enabled is True or str(enabled).casefold() in {"1", "true", "yes", "active"}
        active = active or str(raw.get("state", "")).casefold() == "active"
        return PolicyResult("DISABLE_DATA_FLOW", "ACTIVE" if active else "DISABLED", active)

    if category == "BACKUP_ARCHIVE":
        allowed = raw.get("restore_allowed")
        active = allowed is True or str(allowed).casefold() in {"1", "true", "yes", "active"}
        active = active or str(raw.get("state", "")).casefold() == "active"
        if "eligible" in raw:
            eligible = str(raw.get("eligible")).casefold() in {"1", "true", "yes", "eligible"}
            deletion_block = str(raw.get("deletion_block", "false")).casefold() in {"1", "true", "yes"}
            active = active or (eligible and not deletion_block)
        return PolicyResult("BLOCK_RESTORE", "ACTIVE" if active else "BLOCKED", active)

    if category == "SECURITY_AUDIT_LOG":
        retention_until = raw.get("retention_until")
        if retention_until and str(retention_until) < audit_at:
            action = "DELETE"
        else:
            action = "RETAIN"

    if category == "LEGAL_HOLD_RECORD":
        expiry = raw.get("hold_until") or raw.get("retention_until") or ""
        active = str(raw.get("active", raw.get("hold_status", ""))).casefold() in {
            "true", "1", "active", "on_hold"
        }
        if expiry and expiry >= audit_at:
            active = True
        action = "RETAIN" if active else "DELETE"

    if category == "SUPPORT_MESSAGE":
        shared_context = bool(
            _values(raw, {"order_id", "shared_context", "agent_id"})
            or raw.get("shared_context")
        )
        explicit_state = str(raw.get("state", "")).casefold()
        positive_pii_scan = (
            str(raw.get("event", raw.get("event_type", ""))).casefold() == "message_pii_scan"
            and bool(raw.get("matched_value"))
            and str(raw.get("detector", "")).casefold() == "direct_identifier"
        )
        has_direct_contact = bool(_values(raw, {
            "name", "full_name", "display_name", "email", "owner_email",
            "customer_email", "requester_email", "phone", "owner_phone",
            "requester_phone", "email_hash",
        }))
        action = "REDACT" if (
            shared_context or raw.get("message_excerpt")
            or explicit_state in {"identifiable", "exposed_pii"}
            or positive_pii_scan or has_direct_contact
        ) else "DELETE"

    direct_pii = _values(
        raw,
        {
            "name", "full_name", "display_name", "email", "owner_email",
            "customer_email", "requester_email", "phone", "owner_phone",
            "requester_phone", "email_hash",
        },
    )
    if (
        str(raw.get("event", raw.get("event_type", ""))).casefold()
        in {"message_pii_scan", "analytics_identity_scan"}
        and raw.get("matched_value")
        and str(raw.get("detector", "")).casefold() == "direct_identifier"
    ):
        direct_pii.append(raw["matched_value"])
    has_direct_pii = bool(direct_pii)
    explicitly_identifiable = str(raw.get("state", "")).casefold() in {"identifiable", "exposed_pii"}

    if category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"}:
        links = _values(raw, {
            "user_id", "customer_reference", "subject_reference", "correlation_key",
            "lookup_key", "identity_key", "email_hash",
        })
        known = set().union(*(subject_identifiers or {}).values())
        attributable = has_direct_pii or any(
            str(value).casefold() == (subject_id or "").casefold()
            or str(value).strip().casefold() in known
            for value in links
        )
        attributable = attributable or explicitly_identifiable
        state = "IDENTIFIABLE" if attributable else "ANONYMIZED"
        return PolicyResult(action or "ANONYMIZE", state, attributable)

    if action == "REDACT":
        violation = has_direct_pii or explicitly_identifiable
        state = "IDENTIFIABLE" if violation else "REDACTED"
        return PolicyResult(action, state, violation)
    if action == "ANONYMIZE":
        state = "IDENTIFIABLE" if has_direct_pii else "ANONYMIZED"
        return PolicyResult(action, state, has_direct_pii)
    if action == "RETAIN":
        return PolicyResult(action, "PRESENT", False)
    if action == "DELETE":
        return PolicyResult(action, "PRESENT", True)
    return PolicyResult(action, "PRESENT", False)
