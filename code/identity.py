"""Identity lookup helpers for the deletion audit pipeline."""

from datetime import datetime, timezone
import re
from typing import Iterable, Mapping, Optional


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_email(value: Optional[str]) -> str:
    return (value or "").strip().casefold()


def identifiers_for_user(
    user_id: str,
    identities: Iterable[Mapping[str, str]],
    audit_log: Iterable[Mapping[str, str]],
    audit_at: str,
) -> dict[str, set[str]]:
    """Collect the subject's known identifiers that existed by ``audit_at``."""
    cutoff = _timestamp(audit_at)
    identifiers = {
        "user_id": {user_id.casefold()} if user_id else set(),
        "email": set(),
        "phone": set(),
        "email_hash": set(),
        "name": set(),
    }

    for identity in identities:
        if identity.get("user_id") != user_id:
            continue
        updated_at = identity.get("updated_at")
        if not updated_at or _timestamp(updated_at) > cutoff:
            continue
        for field in ("email", "email_hash", "name"):
            value = (identity.get(field) or "").strip().casefold()
            if value:
                identifiers[field].add(value)
        phone = re.sub(r"\D", "", identity.get("phone") or "")
        if phone:
            identifiers["phone"].add(phone)

    field_map = {
        "email": "email",
        "phone": "phone",
        "email_hash": "email_hash",
    }
    for event in audit_log:
        if event.get("user_id") != user_id:
            continue
        event_time = event.get("event_time")
        field = field_map.get(event.get("field_name", ""))
        if not field or not event_time or _timestamp(event_time) > cutoff:
            continue
        for key in ("old_value", "new_value"):
            value = (event.get(key) or "").strip().casefold()
            if field == "phone":
                value = re.sub(r"\D", "", value)
            if value:
                identifiers[field].add(value)
    return identifiers


def resolve_email(
    email: str,
    identities: Iterable[Mapping[str, str]],
    audit_log: Iterable[Mapping[str, str]],
    audit_at: str,
) -> Optional[str]:
    """Return the unique user whose email history includes ``email`` by cutoff.

    Identity snapshots are usable only when their ``updated_at`` is no later
    than the cutoff. Historical email changes are considered only when their
    event time is at or before the cutoff. Ambiguous matches fail closed.
    """
    needle = _normalize_email(email)
    if not needle:
        return None

    cutoff = _timestamp(audit_at)
    matches = set()

    for identity in identities:
        updated_at = identity.get("updated_at")
        if updated_at and _timestamp(updated_at) <= cutoff:
            if _normalize_email(identity.get("email")) == needle:
                matches.add(identity.get("user_id"))

    for event in audit_log:
        if event.get("field_name") != "email":
            continue
        event_time = event.get("event_time")
        if not event_time or _timestamp(event_time) > cutoff:
            continue
        values = {
            _normalize_email(event.get("old_value")),
            _normalize_email(event.get("new_value")),
        }
        if needle in values:
            matches.add(event.get("user_id"))

    matches.discard(None)
    return next(iter(matches)) if len(matches) == 1 else None
