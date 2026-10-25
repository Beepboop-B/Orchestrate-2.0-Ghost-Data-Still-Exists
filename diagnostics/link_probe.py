"""Diagnostic-only comparison of identity-link techniques against public misses.

This script reads participant inputs and evidence to propose resource candidates.
It reads the public sample answers/per-case miss table only after candidate
generation, for evaluation. It never writes production predictions or output.csv.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.audit import IDENTIFIER_FIELDS, MULTI_IDENTIFIER_FIELDS, _digits, _matches_raw, _text_matches
from code.authorization import authorizes_deletion
from code.data import SCHEMAS, load_csv, load_dataset
from code.engine import audit_request
from code.evidence import load_evidence_files
from code.identity import identifiers_for_user, resolve_email
from code.main import predict


STEP_FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")
TECHNIQUES = ("trace_current", "trace_history", "json_record_current", "history_record")


def _eligible(record, audit_at):
    captured = str(record.get("captured_at") or "")
    observed = str(record.get("observed_at") or captured)
    return bool(captured and observed and captured <= audit_at and observed <= audit_at)


def _current_identifiers(user_id, identities, audit_log, audit_at):
    all_ids = identifiers_for_user(user_id, identities, audit_log, audit_at)
    current = {key: set() for key in all_ids}
    if user_id:
        current["user_id"].add(user_id.casefold())
    for row in identities:
        if row.get("user_id") != user_id or not row.get("updated_at") or row["updated_at"] > audit_at:
            continue
        for field in ("name", "email", "email_hash"):
            value = (row.get(field) or "").strip().casefold()
            if value:
                current[field].add(value)
        phone = _digits(row.get("phone"))
        if phone:
            current["phone"].add(phone)
    historical = {key: values - current.get(key, set()) for key, values in all_ids.items()}
    # Stable user IDs are explicit subject identifiers even though they do not
    # change in the identity audit log.
    historical["user_id"].add(user_id.casefold())
    return current, historical, all_ids


def _typed_match(raw, identifiers):
    return _matches_raw(raw, identifiers)


def _text_match(record, identifiers):
    return _text_matches(str(record.get("text") or ""), identifiers)


def _add_candidate(target, case_id, record, technique, identity_source=None):
    key = (case_id, str(record.get("system_id") or ""), str(record.get("resource_id") or ""))
    if not key[1] or not key[2]:
        return
    item = target.setdefault(key, {"techniques": set(), "evidence": set(), "identity_evidence": set(), "times": set()})
    item["techniques"].add(technique)
    item["evidence"].add(str(record.get("file_id") or ""))
    if identity_source:
        item["identity_evidence"].add(str(identity_source.get("file_id") or ""))
    item["times"].add((str(record.get("captured_at") or ""), str(record.get("observed_at") or "")))
    if identity_source:
        item["times"].add((str(identity_source.get("captured_at") or ""), str(identity_source.get("observed_at") or "")))


def _extract_link_value(raw, identifiers):
    """Return the actual raw identifier value that makes a record match."""
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, (dict, list)):
                found = _extract_link_value(value, identifiers)
                if found:
                    return found
                continue
            if value in (None, ""):
                continue
            normalized_key = key.casefold()
            field = IDENTIFIER_FIELDS.get(normalized_key)
            if field:
                normalized = _digits(value) if field == "phone" else str(value).strip().casefold()
                if normalized and normalized in identifiers.get(field, set()):
                    return str(value)
            elif normalized_key in MULTI_IDENTIFIER_FIELDS or normalized_key == "correlation_key":
                normalized = str(value).strip().casefold()
                if any(normalized in identifiers.get(f, set()) for f in ("user_id", "email", "email_hash")):
                    return str(value)
                digits = _digits(value)
                if digits and digits in identifiers.get("phone", set()):
                    return str(value)
    elif isinstance(raw, list):
        for value in raw:
            found = _extract_link_value(value, identifiers)
            if found:
                return found
    return None


def _candidates(requests, dataset, evidence):
    candidates = {name: {} for name in TECHNIQUES}
    request_info = {}
    trace_enrichment = {"trace_current": defaultdict(list), "trace_history": defaultdict(list)}

    for request in requests:
        case_id = request["case_id"]
        if not authorizes_deletion(request.get("request_text", "")):
            continue
        user_id = resolve_email(request.get("email", ""), dataset["identities"], dataset["audit_log"], request["audit_at"])
        if not user_id:
            continue
        current, historical, all_ids = _current_identifiers(
            user_id, dataset["identities"], dataset["audit_log"], request["audit_at"]
        )
        request_info[case_id] = {"user_id": user_id, "current": current, "historical": historical, "all": all_ids}

        # B: each JSON record is matched in isolation. No identity value is
        # allowed to leak across sibling records in the enclosing bundle.
        for record in evidence:
            if not _eligible(record, request["audit_at"]):
                continue
            if Path(str(record.get("source_path") or "")).suffix.casefold() != ".json":
                continue
            if _typed_match(record.get("raw", {}), current) or _text_match(record, current):
                _add_candidate(candidates["json_record_current"], case_id, record, "json_record_current")

        # C: old email/phone/hash values from user_audit_log plus the stable
        # user_id. Each record is matched independently and remains cutoff-bound.
        for record in evidence:
            if not _eligible(record, request["audit_at"]):
                continue
            if _typed_match(record.get("raw", {}), historical) or _text_match(record, historical):
                _add_candidate(candidates["history_record"], case_id, record, "history_record")

        # A: require a requester-matching record and a separate resource-bearing
        # record with the same explicit trace_id in the same manifest file.
        trace_groups = defaultdict(list)
        for index, record in enumerate(evidence):
            if not _eligible(record, request["audit_at"]):
                continue
            raw = record.get("raw", {})
            trace_id = raw.get("trace_id") if isinstance(raw, dict) else None
            if trace_id:
                trace_groups[(record.get("file_id"), str(trace_id))].append((index, record))
        for (_file_id, _trace), group in trace_groups.items():
            for method, identifiers in (("trace_current", current), ("trace_history", all_ids)):
                linked_sources = [
                    (index, record) for index, record in group
                    if _typed_match(record.get("raw", {}), identifiers) or _text_match(record, identifiers)
                ]
                for index, target in group:
                    if not target.get("resource_id") or not target.get("system_id"):
                        continue
                    for source_index, source in linked_sources:
                        if index == source_index:
                            continue
                        link_value = _extract_link_value(source.get("raw", {}), identifiers)
                        if not link_value:
                            continue
                        _add_candidate(candidates[method], case_id, target, method, source)
                        trace_enrichment[method][case_id].append((index, link_value, source, target))
                        break

    return candidates, request_info, trace_enrichment


def _candidate_rows(candidates, requests, expected_resources, missing_resources):
    request_by = {r["case_id"]: r for r in requests}
    rows = []
    for technique, mapping in candidates.items():
        for (case_id, system_id, resource_id), item in sorted(mapping.items()):
            request = request_by[case_id]
            expected_any = (case_id, system_id, resource_id) in expected_resources
            expected_missing = (case_id, system_id, resource_id) in missing_resources
            rows.append({
                "technique": technique,
                "case_id": case_id,
                "system_id": system_id,
                "resource_id": resource_id,
                "expected_missing_resource": str(expected_missing).lower(),
                "appears_in_any_expected_step": str(expected_any).lower(),
                "identity_relationship": "explicit same-record identifiers" if technique != "trace_current" else "explicit requester identifier and separate resource record share trace_id",
                "evidence_ids": ";".join(sorted(x for x in item["evidence"] if x)),
                "identity_evidence_ids": ";".join(sorted(x for x in item["identity_evidence"] if x)),
                "capture_and_observation_times": ";".join(f"{a}|{b}" for a,b in sorted(item["times"])),
                "eligible_at_audit_at": "true" if all(a and b and a <= request["audit_at"] and b <= request["audit_at"] for a,b in item["times"]) else "false",
                "audit_at": request["audit_at"],
            })
    return rows


def _metrics(predictions, expected_rows):
    expected_by = {r["case_id"]: r for r in expected_rows}
    actual_by = {p["case_id"]: p for p in predictions}
    status_correct = step_count_correct = sequence_correct = 0
    field_correct = field_total = missing = extra = 0
    expected_miss_counts = Counter()
    for case_id, expected in expected_by.items():
        expected_steps = json.loads(expected["steps_json"])
        actual_steps = actual_by[case_id]["steps"]
        status_correct += actual_by[case_id]["deletion_status"] == expected["deletion_status"]
        step_count_correct += len(actual_steps) == len(expected_steps)
        sequence_correct += actual_steps == expected_steps
        for i in range(min(len(actual_steps), len(expected_steps))):
            for field in STEP_FIELDS:
                field_total += 1
                field_correct += actual_steps[i].get(field) == expected_steps[i].get(field)
        expected_groups = Counter((s["phase"],s["system_id"],s["resource_id"]) for s in expected_steps)
        actual_groups = Counter((s["phase"],s["system_id"],s["resource_id"]) for s in actual_steps)
        for key in expected_groups.keys() | actual_groups.keys():
            missing += max(0, expected_groups[key]-actual_groups[key])
            extra += max(0, actual_groups[key]-expected_groups[key])
            if expected_groups[key] > actual_groups[key]:
                expected_miss_counts[(case_id,*key)] += expected_groups[key]-actual_groups[key]
    n=len(expected_by)
    return {"status":(status_correct,n),"step_count":(step_count_correct,n),"fields":(field_correct,field_total),"sequence":(sequence_correct,n),"missing":missing,"extra":extra,"missing_keys":expected_miss_counts}


def _trace_augmented_predictions(requests, dataset, evidence, trace_enrichment):
    predictions=[]
    for request in requests:
        case_id=request["case_id"]
        enriched=deepcopy(evidence)
        for index, link_value, _source, _target in trace_enrichment.get(case_id, []):
            enriched[index].setdefault("raw", {})["subject_key"] = link_value
        predictions.append(audit_request(request,dataset,enriched))
    return predictions


def _format_metrics(label, metrics):
    status=metrics["status"]; counts=metrics["fields"]
    return (f"- {label}: status {status[0]}/{status[1]}, step count {metrics['step_count'][0]}/{metrics['step_count'][1]}, "
            f"fields {counts[0]}/{counts[1]} ({counts[0]/counts[1]:.2%}), sequence {metrics['sequence'][0]}/{metrics['sequence'][1]}, "
            f"missing {metrics['missing']}, extra {metrics['extra']}.")


def run():
    dataset_dir=ROOT/"dataset"
    dataset=load_dataset(dataset_dir)
    evidence=load_evidence_files(dataset_dir,dataset["evidence_manifest"])
    requests=dataset["sample_requests"]
    candidates, request_info, trace_enrichment=_candidates(requests,dataset,evidence)

    # Evaluation target is opened only after all candidate sets are generated.
    expected_rows=load_csv(dataset_dir/"sample_output.csv",("case_id","deletion_status","steps_json"))
    expected_resources=set()
    expected_steps=set()
    for row in expected_rows:
        for step in json.loads(row["steps_json"]):
            expected_resources.add((row["case_id"],step["system_id"],step["resource_id"]))
            expected_steps.add((row["case_id"],step["phase"],step["system_id"],step["resource_id"],step["operation"],step["state"]))
    with (ROOT/"diagnostics/per_case_misses.csv").open(encoding="utf-8-sig",newline="") as f:
        miss_rows=list(csv.DictReader(f))
    missing_rows=[r for r in miss_rows if r["expected_resource_id"]]
    missing_resources={(r["case_id"],r["expected_system_id"],r["expected_resource_id"]) for r in missing_rows}
    missing_step_keys={(r["case_id"],r["expected_phase"],r["expected_system_id"],r["expected_resource_id"],r["expected_operation"],r["expected_state"]) for r in missing_rows}

    candidate_csv=ROOT/"diagnostics/link_probe_candidates.csv"
    rows=_candidate_rows(candidates,requests,expected_resources,missing_resources)
    fields=["technique","case_id","system_id","resource_id","expected_missing_resource","appears_in_any_expected_step","identity_relationship","evidence_ids","identity_evidence_ids","capture_and_observation_times","eligible_at_audit_at","audit_at"]
    with candidate_csv.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    base=[audit_request(request,dataset,evidence) for request in requests]
    trace_trial=_trace_augmented_predictions(requests,dataset,evidence,trace_enrichment["trace_current"])
    history_trace_trial=_trace_augmented_predictions(requests,dataset,evidence,trace_enrichment["trace_history"])
    base_metrics=_metrics(base,expected_rows); trace_metrics=_metrics(trace_trial,expected_rows)
    history_trace_metrics=_metrics(history_trace_trial,expected_rows)
    technique_reports=[]
    for technique in TECHNIQUES:
        mapping=candidates[technique]
        candidate_keys=set(mapping)
        missed=sorted(candidate_keys & missing_resources)
        expected_hits=candidate_keys & expected_resources
        invalid=[key for key,item in mapping.items() if not all(a and b and a<=next(r["audit_at"] for r in requests if r["case_id"]==key[0]) and b<=next(r["audit_at"] for r in requests if r["case_id"]==key[0]) for a,b in item["times"])]
        technique_reports.append((technique,len(candidate_keys),len(missed),len(expected_hits),len(candidate_keys-expected_resources),missed,invalid))

    # Combination is justified only when same-trace evidence carries the
    # explicit subject key; historical values may be the trace's subject key.
    combined_metrics=history_trace_metrics

    # Determine all-518 request impact using the same trace-correlation rule.
    full_enrichment_count=0; full_candidate_count=0; full_requests=dataset["requests"]
    full_candidates, _full_info, full_trace=_candidates(full_requests,dataset,evidence)
    full_candidate_count=len(full_candidates["trace_current"])
    full_enrichment_count=len(full_trace["trace_current"])
    report=ROOT/"diagnostics/link_probe_report.md"
    lines=[
        "# Diagnostic Link Probe",
        "",
        "`link_probe.py` was absent when searched for. This diagnostic-only script uses participant-facing identity, activity, manifest, and evidence data to generate candidate resources. It does not write production predictions. `sample_output.csv` and `per_case_misses.csv` are loaded only after candidate generation for scoring.",
        "",
        "## Candidate techniques",
        "",
        "- `trace_current`: explicit current requester identifier in one eligible evidence record and a separate resource-bearing record sharing the same file-local `trace_id`; no time-proximity joins.",
        "- `trace_history`: same trace rule, allowing historical identifiers and stable user_id as the explicit identity edge.",
        "- `json_record_current`: exact identifier match inside one eligible parsed JSON record; sibling records in the enclosing bundle are never cross-joined.",
        "- `history_record`: exact match against user_audit_log old/new identifiers available by the request cutoff, plus the stable user_id; records remain individually cutoff checked.",
        "",
        "All candidate sources require manifest `captured_at <= audit_at` and record `observed_at <= audit_at`.",
        "",
        "## Candidate recall and precision",
        "",
        "Candidate precision is measured against any expected resource in that case. False candidate count is the number of candidates not present in any expected step. Missing-resource recall is exact overlap with the 29 missing phase-steps' resources.",
        "",
        "| Technique | Candidate resources | Overlap with 29 missing resources | Missing-resource recall | Expected resources matched | Precision | Not in any expected step | Ineligible candidates |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for technique,count,missed,expected_hit,false_count,miss_list,invalid in technique_reports:
        precision=expected_hit/count if count else 0.0
        lines.append(f"| {technique} | {count} | {missed} | {missed}/29 ({missed/29:.2%}) | {expected_hit} | {precision:.2%} | {false_count} | {len(invalid)} |")
    union=set().union(*(set(candidates[t]) for t in TECHNIQUES))
    union_missed=union & missing_resources; union_expected=union & expected_resources
    lines.extend([
        f"| technique union | {len(union)} | {len(union_missed)} | {len(union_missed)}/29 ({len(union_missed)/29:.2%}) | {len(union_expected)} | {(len(union_expected)/len(union) if union else 0):.2%} | {len(union-expected_resources)} | {sum(1 for r in rows if r['eligible_at_audit_at']=='false')} |",
        "",
        "## End-to-end sample metrics",
        "",
        _format_metrics("Current production baseline",base_metrics),
        _format_metrics("Trace-correlation candidate enrichment",trace_metrics),
        _format_metrics("Trace plus history combination",combined_metrics),
        "- Record-level nested JSON and historical identifier matching are already active in production (`find_matching_evidence` and `identifiers_for_user`), so their isolated end-to-end result is the baseline; adding them again makes no candidate change.",
        "",
        "Newly recovered exact missing phase-steps under trace enrichment: " + str(sorted(set(base_metrics["missing_keys"]) - set(trace_metrics["missing_keys"]))) + ".",
        "Newly recovered exact missing phase-steps under trace plus history: " + str(sorted(set(base_metrics["missing_keys"]) - set(combined_metrics["missing_keys"]))) + ".",
        "",
        "## Full evaluation-set impact",
        "",
        f"Read-only candidate generation over all {len(full_requests)} requests produced {full_candidate_count} trace-linked resource candidates and {full_enrichment_count} candidate enrichments. It did not modify or write output.csv. Requests with any candidate: {len({k[0] for k in full_candidates['trace_current']})}.",
        "",
        "## Candidate evidence detail",
        "",
        f"Per-candidate linkage/provenance/eligibility details are in `{candidate_csv.name}`. Each row identifies the candidate method, source evidence IDs, capture and observation times, cutoff eligibility, and overlap with expected missing/all expected resources.",
        "",
        "## Decision",
        "",
        "No new production rule is justified by this probe unless a candidate adds an explicit identity edge supported by eligible participant evidence and improves exact ordered sequences without false candidates. Trace propagation is diagnostic-only here; JSON record-boundary matching and historical identity resolution already exist in production. The probe never accepts a later manifest capture because of a nested observed_at value.",
    ])
    report.write_text("\n".join(lines)+"\n",encoding="utf-8")

    print("Prototype present before work: no; created diagnostics/link_probe.py")
    print("Missing phase-step rows:",len(missing_rows))
    for technique,count,missed,expected_hit,false_count,miss_list,invalid in technique_reports:
        print(f"{technique}: candidates={count}, exact-missing-overlap={missed}, expected-resource-matches={expected_hit}, nonexpected={false_count}, ineligible={len(invalid)}")
        if miss_list:
            print("  matched misses:",miss_list)
    print(_format_metrics("baseline",base_metrics))
    print(_format_metrics("trace enrichment",trace_metrics))
    print(f"Full requests: {len(full_requests)}; trace candidates={full_candidate_count}; requests affected={len({k[0] for k in full_candidates['trace_current']})}; enrichments={full_enrichment_count}")
    print("Reports:",report,candidate_csv)


if __name__ == "__main__":
    run()
