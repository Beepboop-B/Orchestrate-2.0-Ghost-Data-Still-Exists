"""Readers for the participant-facing evidence formats."""

import base64
import json
import re
import shlex
import sqlite3
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional


TABLE_SYSTEMS = {
    "customer_profiles": "account_service",
    "customer_profiles_primary": "account_service",
    "customer_profiles_failover_replica": "account_service",
    "customer_analytics_profiles": "analytics_platform",
    "customer_search_documents": "search_service",
    "support_records": "support_platform",
    "backup_restore_entries": "backup_service",
    "connector_subscriptions": "integration_service",
    "security_audit_records": "security_service",
    "customer_exports": "export_service",
}


def _system_for_table(table: str) -> Optional[str]:
    """Infer a source system for known participant-facing snapshot table names."""
    if table in TABLE_SYSTEMS:
        return TABLE_SYSTEMS[table]
    normalized = table.casefold()
    prefixes = (
        ("customer_profiles", "account_service"),
        ("search_documents", "search_service"),
        ("customer_search", "search_service"),
        ("support_records", "support_platform"),
        ("analytics", "analytics_platform"),
        ("customer_analytics", "analytics_platform"),
        ("customer_exports", "export_service"),
        ("connector", "integration_service"),
        ("security_audit", "security_service"),
        ("backup_restore", "backup_service"),
    )
    return next((system for prefix, system in prefixes if normalized.startswith(prefix)), None)


def _canonical_system(system_id: Optional[str]) -> Optional[str]:
    value = str(system_id or "")
    aliases = {
        "support_replica": "support_platform",
        "support_service": "support_platform",
        "user_export_store": "export_service",
        "export_store": "export_service",
        "profile_service": "account_service",
        "identity_store": "identity_service",
        "analytics_identity_store": "analytics_platform",
    }
    return aliases.get(value, value or None)


def _record(
    raw: Dict[str, Any],
    file_id: str,
    source_path: Path,
    captured_at: str,
    system_id: Optional[str] = None,
    collection: Optional[str] = None,
    observed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Attach envelope availability separately from a source observation time.

    ``captured_at`` is the manifest capture time for the evidence file. A nested
    snapshot timestamp is retained as ``observed_at``; it does not make a later
    evidence file available earlier than its manifest capture.
    """
    return {
        "file_id": file_id,
        "source_path": str(source_path),
        "captured_at": captured_at,
        "observed_at": observed_at or _first_timestamp(raw) or captured_at,
        "system_id": _canonical_system(raw.get("system") or system_id),
        "collection": raw.get("collection") or collection or "",
        "resource_id": raw.get("resource_id"),
        "raw": raw,
    }


def _first_timestamp(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        for key in ("observed_at", "recorded_at", "captured_at", "event_time"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
    return None


def _parse_json(
    obj: Any, file_id: str, source_path: Path, captured_at: str
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    def visit(
        node: Any,
        system_id: Optional[str] = None,
        collection: Optional[str] = None,
        inherited_time: Optional[str] = None,
    ) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item, system_id, collection, inherited_time)
            return
        if not isinstance(node, dict):
            return

        local_time = node.get("captured_at") or node.get("observed_at") or inherited_time

        # Snapshot bundles explicitly name their source system and collection.
        if isinstance(node.get("records"), list):
            child_system = node.get("data_store") or node.get("system") or system_id
            child_collection = node.get("collection") or collection
            for item in node["records"]:
                if isinstance(item, dict):
                    records.append(
                        _record(
                            item,
                            file_id,
                            source_path,
                            captured_at,
                            child_system,
                            child_collection,
                            local_time,
                        )
                    )
                    # Nested documents and payloads carry identity fields too.
                    visit_nested(item, child_system, child_collection, local_time)
            for key, value in node.items():
                if key != "records":
                    visit(value, child_system, child_collection, local_time)
            return

        # Service exports group record lists under their service names.
        for key, value in node.items():
            if isinstance(value, dict) and key.endswith(("_service", "_platform")):
                visit(value, key, None, local_time)
            elif isinstance(value, list) and value and all(
                isinstance(item, dict) for item in value
            ):
                for item in value:
                    if item.get("resource_id"):
                        records.append(
                            _record(
                                item,
                                file_id,
                                source_path,
                                captured_at,
                                system_id,
                                key,
                                local_time,
                            )
                        )
                        visit_nested(item, system_id, key, local_time)
                    else:
                        visit(item, system_id, key, local_time)
            elif isinstance(value, (dict, list)):
                visit(value, system_id, collection, local_time)

    def visit_nested(
        node: Any,
        system_id: Optional[str],
        collection: Optional[str],
        inherited_time: Optional[str],
    ) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, dict) and value.get("resource_id"):
                    records.append(
                        _record(
                            value,
                            file_id,
                            source_path,
                            captured_at,
                            system_id,
                            key,
                            inherited_time,
                        )
                    )
                elif isinstance(value, (dict, list)):
                    visit_nested(value, system_id, key, inherited_time)
        elif isinstance(node, list):
            for value in node:
                visit_nested(value, system_id, collection, inherited_time)

    root_system = None
    if isinstance(obj, dict):
        root_system = obj.get("source") or obj.get("origin")
    visit(obj, root_system)
    return records


def _parse_sql(
    source_path: Path, file_id: str, captured_at: str
) -> List[Dict[str, Any]]:
    db = sqlite3.connect(":memory:")
    try:
        db.executescript(source_path.read_text(encoding="utf-8"))
        tables = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        snapshot_time = captured_at
        scope_records = []
        if "snapshot_scope" in tables:
            for origin_system, captured in db.execute(
                "SELECT origin_system, captured_at FROM snapshot_scope"
            ):
                if captured:
                    snapshot_time = captured
                scope_records.append(
                    _record(
                        {
                            "origin_system": origin_system,
                            "captured_at": captured or snapshot_time,
                        },
                        file_id,
                        source_path,
                        snapshot_time,
                        origin_system,
                        "snapshot_scope",
                        captured or snapshot_time,
                    )
                )

        records = list(scope_records)
        for table in tables:
            if table == "snapshot_scope":
                continue
            columns = [row[1] for row in db.execute(f'PRAGMA table_info("{table}")')]
            table_rows = [dict(zip(columns, values)) for values in db.execute(f'SELECT * FROM "{table}"')]
            if table in {"customer_data_primary", "customer_data_failover_replica", "customer_data_reporting_replica", "customer_data_replica_ap_south", "customer_data_replica_eu_west"}:
                scope_pairs = {
                    (row.get("origin_system", ""), row.get("collection_name", ""))
                    for row in table_rows
                    if row.get("origin_system") and row.get("collection_name")
                }
                for origin, collection in sorted(scope_pairs):
                    records.append(
                        _record(
                            {"scope": True, "scope_system": origin, "scope_collection": collection},
                            file_id,
                            source_path,
                            snapshot_time,
                            origin,
                            collection,
                            snapshot_time,
                        )
                    )
            else:
                table_system = _system_for_table(table)
                if table_system:
                    records.append(
                        _record(
                            {"scope": True, "scope_system": table_system, "scope_collection": table},
                            file_id,
                            source_path,
                            snapshot_time,
                            table_system,
                            table,
                            snapshot_time,
                        )
                    )
            for raw in table_rows:
                if isinstance(raw.get("record_json"), str):
                    try:
                        payload = json.loads(raw["record_json"])
                        if isinstance(payload, dict):
                            raw.update(payload)
                    except json.JSONDecodeError:
                        pass
                origin = raw.get("origin_system")
                system_id = origin or _system_for_table(table)
                collection = raw.get("collection_name") or table
                records.append(
                    _record(raw, file_id, source_path, snapshot_time, system_id, collection)
                )
        if not records:
            records.append(
                _record({}, file_id, source_path, captured_at, None, "empty_snapshot")
            )
        return records
    finally:
        db.close()


def _pdf_text(source_path: Path) -> str:
    data = source_path.read_bytes()
    pieces = []
    stream_pattern = re.compile(rb"<<(.*?)>>\s*stream\r?\n(.*?)endstream", re.S)
    literal_pattern = re.compile(rb"\(((?:\\.|[^\\)])*)\)\s*Tj")
    for match in stream_pattern.finditer(data):
        dictionary, stream = match.group(1), match.group(2).rstrip(b"\r\n")
        try:
            if b"ASCII85Decode" in dictionary:
                stream = base64.a85decode(stream, adobe=True)
            if b"FlateDecode" in dictionary:
                stream = zlib.decompress(stream)
        except (ValueError, zlib.error):
            continue
        if b"BT" not in stream:
            continue
        for token in literal_pattern.findall(stream):
            token = re.sub(rb"\\([()\\])", rb"\1", token)
            token = token.replace(b"\\n", b" ").replace(b"\\r", b" ")
            pieces.append(token.decode("latin-1", errors="replace"))
    return " ".join(pieces)


def _parse_text_records(
    source_path: Path, file_id: str, captured_at: str, text: str
) -> List[Dict[str, Any]]:
    records = []
    handover_pattern = re.compile(
        r"^\s*-?\s*(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\s*\|\s*"
        r"([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*$"
    )
    for line in text.splitlines():
        timestamp = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line)
        json_start = line.find("{")
        if timestamp and json_start >= 0:
            try:
                payload = json.loads(line[json_start:])
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                event = str(payload.get("event", payload.get("event_type", ""))).casefold()
                system = _canonical_system(
                    payload.get("service") or payload.get("system_id") or payload.get("logger")
                )
                resource_id = payload.get("resource_id")
                if resource_id or (
                    payload.get("trace_id") and event.endswith("_started")
                ):
                    records.append({
                        "file_id": file_id,
                        "source_path": str(source_path),
                        "captured_at": captured_at,
                        "observed_at": timestamp.group(1),
                        "system_id": system,
                        "collection": event or "text_log",
                        "resource_id": resource_id,
                        "text": line.strip(),
                        "raw": payload,
                    })
                continue
        match = handover_pattern.match(line)
        if match:
            observed_at, system, resource, category, state, subject = match.groups()
            raw = {
                "system_id": system.strip(),
                "resource_id": resource.strip(),
                "data_category": category.strip(),
                "state": state.strip(),
                "subject_reference": subject.strip(),
                "text": line.strip(),
            }
            records.append(
                {
                    "file_id": file_id,
                    "source_path": str(source_path),
                    "captured_at": captured_at,
                    "observed_at": observed_at,
                    "system_id": system.strip(),
                    "collection": category.strip(),
                    "resource_id": resource.strip(),
                    "text": line.strip(),
                    "raw": raw,
                }
            )
            continue

        try:
            tokens = shlex.split(line)
        except ValueError:
            tokens = []
        fields = {}
        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                fields[key] = value
        resource_id = fields.get("resource_id")
        if not resource_id:
            if fields.get("trace_id") and str(fields.get("event", "")).casefold().endswith("_started"):
                records.append({
                    "file_id": file_id,
                    "source_path": str(source_path),
                    "captured_at": captured_at,
                    "observed_at": timestamp.group(1) if (timestamp := re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line)) else captured_at,
                    "system_id": _canonical_system(fields.get("service") or fields.get("system_id") or fields.get("source_system")),
                    "collection": fields.get("event") or "text_log",
                    "resource_id": None,
                    "text": line.strip(),
                    "raw": fields,
                })
            continue
        timestamp = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line)
        observed_at = timestamp.group(1) if timestamp else captured_at
        system = _canonical_system(fields.get("service") or fields.get("system_id") or fields.get("source_system"))
        fields["text"] = line.strip()
        records.append(
            {
                "file_id": file_id,
                "source_path": str(source_path),
                "captured_at": captured_at,
                "observed_at": observed_at,
                "system_id": system,
                "collection": fields.get("event") or fields.get("event_type") or "text_log",
                "resource_id": resource_id,
                "text": line.strip(),
                "raw": fields,
            }
        )
    # Preserve the complete participant-facing artifact for evidence search.
    records.append(
        {
            "file_id": file_id,
            "source_path": str(source_path),
            "captured_at": captured_at,
            "observed_at": captured_at,
            "system_id": None,
            "collection": "text_log",
            "resource_id": None,
            "text": text,
            "raw": {},
        }
    )
    _propagate_trace_identity(records)
    return records


def _propagate_trace_identity(records: List[Dict[str, Any]]) -> None:
    """Attach identity keys from a trace's starting event to its resource events."""
    starts = {}
    identity_fields = {
        "lookup_key", "subject_key", "subject_ref", "correlation_key", "match_key",
        "email", "customer_email", "requester_email", "phone", "customer_reference",
        "user_id", "email_hash", "name",
    }
    for item in records:
        raw = item.get("raw", {})
        event = str(raw.get("event", "")).casefold()
        trace_id = raw.get("trace_id")
        if trace_id and (event.endswith("_started") or event.endswith("_scan_started")):
            starts[trace_id] = raw
    for item in records:
        raw = item.get("raw", {})
        if raw.get("trace_id") in starts:
            for key, value in starts[raw["trace_id"]].items():
                if key in identity_fields and key not in raw:
                    raw[key] = value


def parse_evidence_file(
    source_path: Path, file_id: str, captured_at: str, origin: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Parse a participant-facing evidence file into provenance-bearing records."""
    source_path = Path(source_path)
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        obj = json.loads(source_path.read_text(encoding="utf-8"))
        return _parse_json(obj, file_id, source_path, captured_at)
    if suffix == ".sql":
        return _parse_sql(source_path, file_id, captured_at)
    if suffix == ".pdf":
        text = _pdf_text(source_path)
        resource_match = re.search(r"\b(?:support|attachment|case)[_-]\d+\b", text, re.IGNORECASE)
        resource_id = resource_match.group(0) if resource_match else None
        collection = "support_attachment" if "attachment" in source_path.stem.casefold() else "document"
        return [
            {
                "file_id": file_id,
                "source_path": str(source_path),
                "captured_at": captured_at,
                "observed_at": captured_at,
                "system_id": _canonical_system(origin),
                "collection": collection,
                "resource_id": resource_id,
                "text": text,
                "raw": {"resource_id": resource_id} if resource_id else {},
            }
        ]
    if suffix in {".log", ".txt"}:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        return _parse_text_records(source_path, file_id, captured_at, text)
    return [
        {
            "file_id": file_id,
            "source_path": str(source_path),
            "captured_at": captured_at,
            "observed_at": captured_at,
            "system_id": origin,
            "collection": "image",
            "resource_id": None,
            "text": "",
            "raw": {},
        }
    ]


def load_evidence_files(
    dataset_dir: Path, manifest: Iterable[Mapping[str, str]]
) -> List[Dict[str, Any]]:
    """Load manifest-listed evidence while preventing paths outside the dataset."""
    root = Path(dataset_dir).resolve()
    records = []
    ordered = sorted(
        manifest,
        key=lambda row: int(row["file_id"].rsplit("_", 1)[1]),
    )
    for item in ordered:
        source_path = (root / item["file_path"]).resolve()
        if not source_path.is_relative_to(root):
            raise ValueError(f"Evidence path escapes dataset directory: {item['file_path']}")
        records.extend(
            parse_evidence_file(
                source_path,
                item["file_id"],
                item["captured_at"],
                item.get("origin"),
            )
        )
    return records
