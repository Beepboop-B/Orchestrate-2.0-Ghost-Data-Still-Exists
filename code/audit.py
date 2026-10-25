"""Point-in-time identity-to-evidence linking."""

from datetime import datetime, timezone
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from code.identity import identifiers_for_user, resolve_email


IDENTIFIER_FIELDS = {
    "email": "email",
    "owner_email": "email",
    "customer_email": "email",
    "requester_email": "email",
    "email_hash": "email_hash",
    "phone": "phone",
    "owner_phone": "phone",
    "requester_phone": "phone",
    "user_id": "user_id",
    "customer_reference": "user_id",
    "subject_reference": "user_id",
    "subject_ref": "user_id",
    "user_reference": "user_id",
}

MULTI_IDENTIFIER_FIELDS = {
    "lookup_key", "query", "subject_key", "match_key", "identity_key",
}

ACCOUNT_DELETE_WINDOW_SECONDS = 90 * 60
ACCOUNT_DELETE_RESULT_BY_STATUS = {
    "COMPLETE": {"SUCCESS"},
    "NOT_STARTED": {"FAILED"},
    "PARTIALLY_COMPLETE": {"PARTIAL", "SUCCESS"},
}
ACCOUNT_DELETE_BEFORE_REPORT_SECONDS = (0.70 * 3600, 1.30 * 3600)
ACCOUNT_DELETE_AFTER_REPORT_SECONDS = 15 * 60


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def find_account_resource_hint(
    request: Mapping[str, str],
    activities: Sequence[Mapping[str, str]],
    request_universe: Sequence[Mapping[str, str]],
) -> Optional[Tuple[str, str]]:
    """Correlate a unique account deletion event to its reported workflow.

    Activity identifies its target resource and system, while the request gives
    the workflow's reported time. The correlation is accepted only when the
    event can match exactly one eligible activity for this request and exactly
    one request window in the supplied full request universe. The event is only
    a candidate hint: callers must independently reconstruct state from evidence.
    """
    if not request.get("reported_at") or not request.get("requested_at"):
        return None
    try:
        requested_at = _timestamp(request["requested_at"])
        reported_at = _timestamp(request["reported_at"])
        audit_at = _timestamp(request["audit_at"])
    except (KeyError, TypeError, ValueError):
        return None

    candidates = []
    for activity in activities:
        if (
            activity.get("event_type") != "DELETE_RECORD"
            or activity.get("target_system") != "account_service"
            or not activity.get("resource_id")
            or not activity.get("event_time")
        ):
            continue
        try:
            event_time = _timestamp(activity["event_time"])
        except (TypeError, ValueError):
            continue
        if (
            event_time < requested_at
            or event_time > audit_at
            or abs((event_time - reported_at).total_seconds()) > ACCOUNT_DELETE_WINDOW_SECONDS
        ):
            continue
        candidates.append(activity)

    if len(candidates) != 1:
        return None
    activity = candidates[0]

    overlapping_requests = []
    seen_case_ids = set()
    for candidate_request in request_universe:
        case_id = candidate_request.get("case_id")
        if not case_id or case_id in seen_case_ids:
            continue
        seen_case_ids.add(case_id)
        try:
            candidate_time = _timestamp(candidate_request["requested_at"])
            candidate_report = _timestamp(candidate_request["reported_at"])
            candidate_audit = _timestamp(candidate_request["audit_at"])
            event_time = _timestamp(activity["event_time"])
        except (KeyError, TypeError, ValueError):
            continue
        if (
            candidate_time <= event_time <= candidate_audit
            and abs((candidate_report - event_time).total_seconds()) <= ACCOUNT_DELETE_WINDOW_SECONDS
        ):
            overlapping_requests.append(case_id)

    if overlapping_requests != [request.get("case_id")]:
        return None
    return str(activity["resource_id"]), str(activity.get("activity_id", ""))


def find_status_consistent_account_hints(
    activities: Sequence[Mapping[str, str]],
    request_universe: Sequence[Mapping[str, str]],
    exact_account_owners: Optional[Mapping[str, set[str]]] = None,
) -> Dict[str, Tuple[str, str]]:
    """Assign status-consistent primary-profile delete events one-to-one.

    A candidate activity must agree with the request's reported workflow
    status and fall in the bounded window around ``reported_at``. Unique
    request claims propagate by removing the claimed activity from every
    other request's candidate set. Activity remains a candidate hint only;
    callers must establish independent state at the request's ``audit_at``.
    """
    requests = {row.get("case_id"): row for row in request_universe if row.get("case_id")}
    candidates: Dict[str, List[Mapping[str, str]]] = {}

    for case_id, request in requests.items():
        eligible_results = ACCOUNT_DELETE_RESULT_BY_STATUS.get(
            str(request.get("reported_status", "")).upper(), set()
        )
        matches = []
        if not eligible_results:
            candidates[case_id] = matches
            continue
        try:
            requested_at = _timestamp(request["requested_at"])
            reported_at = _timestamp(request["reported_at"])
            audit_at = _timestamp(request["audit_at"])
        except (KeyError, TypeError, ValueError):
            candidates[case_id] = matches
            continue

        for activity in activities:
            if (
                activity.get("event_type") != "DELETE_RECORD"
                or activity.get("target_system") != "account_service"
                or not activity.get("resource_id")
                or activity.get("reported_result") not in eligible_results
                or not activity.get("activity_id")
                or not activity.get("event_time")
            ):
                continue
            # If participant evidence exactly ties this account to another
            # requester's email or stable user ID, it cannot be claimed here.
            owners = (exact_account_owners or {}).get(str(activity["resource_id"]), set())
            if owners and case_id not in owners:
                continue
            try:
                event_time = _timestamp(activity["event_time"])
            except (TypeError, ValueError):
                continue
            delta = (reported_at - event_time).total_seconds()
            near_report = (
                ACCOUNT_DELETE_BEFORE_REPORT_SECONDS[0]
                <= delta
                <= ACCOUNT_DELETE_BEFORE_REPORT_SECONDS[1]
            ) or (-ACCOUNT_DELETE_AFTER_REPORT_SECONDS <= delta <= 0)
            if requested_at <= event_time <= audit_at and near_report:
                matches.append(activity)
        candidates[case_id] = matches

    resolved: Dict[str, Mapping[str, str]] = {}
    while True:
        claims: Dict[str, List[str]] = {}
        for case_id, options in candidates.items():
            if case_id not in resolved and len(options) == 1:
                activity_id = str(options[0]["activity_id"])
                claims.setdefault(activity_id, []).append(case_id)
        unique_claims = {
            activity_id: case_ids[0]
            for activity_id, case_ids in claims.items()
            if len(case_ids) == 1
        }
        if not unique_claims:
            break
        for activity_id, case_id in unique_claims.items():
            resolved[case_id] = candidates[case_id][0]
        claimed_ids = set(unique_claims)
        for case_id, options in candidates.items():
            if case_id not in resolved:
                candidates[case_id] = [
                    activity for activity in options
                    if str(activity.get("activity_id", "")) not in claimed_ids
                ]

    return {
        case_id: (str(activity["resource_id"]), str(activity["activity_id"]))
        for case_id, activity in resolved.items()
    }


def find_exact_account_owners(
    evidence: Sequence[Mapping[str, Any]],
    requests: Sequence[Mapping[str, str]],
    identities: Sequence[Mapping[str, str]],
    audit_log: Sequence[Mapping[str, str]],
) -> Dict[str, set[str]]:
    """Map account resources to cases using exact identity-bearing evidence.

    Current and historical emails and stable user IDs are considered, along
    with historical phone/hash values from the audit log. Names, current
    phone/hash values, trace proximity, and time windows are excluded.
    """
    owners: Dict[str, set[str]] = {}
    for request in requests:
        user_id = resolve_email(
            request.get("email", ""), identities, audit_log, request["audit_at"]
        )
        if not user_id:
            continue
        identifiers = identifiers_for_user(user_id, identities, audit_log, request["audit_at"])
        historical = {"email": set(), "phone": set(), "email_hash": set()}
        for change in audit_log:
            if change.get("user_id") != user_id or change.get("event_time", "") > request["audit_at"]:
                continue
            field = str(change.get("field_name", ""))
            if field not in historical:
                continue
            for key in ("old_value", "new_value"):
                value = str(change.get(key) or "").strip().casefold()
                if field == "phone":
                    value = _digits(value)
                if value:
                    historical[field].add(value)
        exact_identifiers = {
            "user_id": identifiers["user_id"],
            "email": identifiers["email"],
            "phone": historical["phone"],
            "email_hash": historical["email_hash"],
            "name": set(),
        }
        for record in evidence:
            captured = str(record.get("captured_at") or "")
            observed = str(record.get("observed_at") or captured)
            if (
                record.get("system_id") != "account_service"
                or not record.get("resource_id")
                or not captured or captured > request["audit_at"]
                or observed > request["audit_at"]
                or not _matches_exact_email_or_user_id(record.get("raw", {}), exact_identifiers)
            ):
                continue
            owners.setdefault(str(record["resource_id"]), set()).add(str(request["case_id"]))
    return owners


def _matches_exact_email_or_user_id(raw: Any, identifiers: Mapping[str, set[str]]) -> bool:
    """Match explicit fields or boundary-delimited exact identifiers in text."""
    if isinstance(raw, dict):
        for key, value in raw.items():
            normalized_key = str(key).casefold()
            field = IDENTIFIER_FIELDS.get(normalized_key)
            if field in {"email", "user_id", "phone", "email_hash"} and value not in (None, ""):
                normalized = _digits(value) if field == "phone" else str(value).strip().casefold()
                if normalized in identifiers.get(field, set()):
                    return True
            if normalized_key in MULTI_IDENTIFIER_FIELDS | {"correlation_key"} and value not in (None, ""):
                normalized = str(value).strip().casefold()
                if any(normalized in identifiers.get(field, set()) for field in ("email", "user_id", "email_hash")):
                    return True
                digits = _digits(value)
                if digits and digits in identifiers.get("phone", set()):
                    return True
            if normalized_key == "text" and isinstance(value, str):
                for field in ("email", "user_id", "email_hash"):
                    for identifier in identifiers.get(field, set()):
                        boundary = r"(?<![\w.+-])" if field == "email" else r"(?<!\w)"
                        trailing = r"(?![\w.-])" if field == "email" else r"(?!\w)"
                        if re.search(boundary + re.escape(identifier) + trailing, value, re.IGNORECASE):
                            return True
                phone_digits = _digits(value)
                if any(
                    phone and re.search(r"(?<!\d)" + re.escape(phone) + r"(?!\d)", phone_digits)
                    for phone in identifiers.get("phone", set())
                ):
                    return True
            if _matches_exact_email_or_user_id(value, identifiers):
                return True
    elif isinstance(raw, list):
        return any(_matches_exact_email_or_user_id(value, identifiers) for value in raw)
    return False


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _matches_raw(raw: Any, identifiers: Mapping[str, set[str]]) -> bool:
    if isinstance(raw, dict):
        for key, value in raw.items():
            normalized_key = key.casefold()
            field = IDENTIFIER_FIELDS.get(normalized_key)
            if field and value not in (None, ""):
                normalized = _digits(value) if field == "phone" else str(value).strip().casefold()
                if normalized and normalized in identifiers.get(field, set()):
                    return True
            if normalized_key in MULTI_IDENTIFIER_FIELDS and value not in (None, ""):
                normalized = str(value).strip().casefold()
                if normalized and any(
                    normalized in identifiers.get(identifier, set())
                    for identifier in ("user_id", "email", "email_hash")
                ):
                    return True
                digits = _digits(value)
                if digits and digits in identifiers.get("phone", set()):
                    return True
            if key.casefold() == "correlation_key" and value not in (None, ""):
                normalized = str(value).strip().casefold()
                if any(normalized in identifiers.get(field, set()) for field in ("user_id", "email", "email_hash")):
                    return True
            if _matches_raw(value, identifiers):
                return True
    elif isinstance(raw, list):
        return any(_matches_raw(value, identifiers) for value in raw)
    return False


def _text_matches(text: str, identifiers: Mapping[str, set[str]]) -> bool:
    folded = (text or "").casefold()
    if any(value and value in folded for value in identifiers.get("email", set())):
        return True
    if any(value and value in folded for value in identifiers.get("email_hash", set())):
        return True
    for user_id in identifiers.get("user_id", set()):
        if user_id and re.search(rf"(?<![\w]){re.escape(user_id)}(?![\w])", folded):
            return True
    for name in identifiers.get("name", set()):
        normalized = " ".join(str(name).casefold().split())
        if len(normalized) >= 5 and normalized in " ".join(folded.split()):
            return True
    digits = _digits(text)
    return any(value and value in digits for value in identifiers.get("phone", set()))


def find_matching_evidence(
    records: Iterable[Mapping[str, Any]],
    identifiers: Mapping[str, set[str]],
    audit_at: str,
) -> List[Dict[str, Any]]:
    """Return exact-identifier matches available and observed by the cutoff.

    The manifest/file capture time and the record's source observation time
    are independent bounds; both must be at or before ``audit_at``.
    """
    matches = []
    for record in records:
        captured = record.get("captured_at") or ""
        observed = record.get("observed_at") or captured
        if not captured or captured > audit_at or observed > audit_at:
            continue
        raw = record.get("raw", {})
        if _matches_raw(raw, identifiers) or _text_matches(
            str(record.get("text", "")), identifiers
        ):
            matches.append(dict(record))
    return matches


