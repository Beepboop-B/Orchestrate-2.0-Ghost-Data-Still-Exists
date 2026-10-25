"""Compare generated public-sample predictions with their supplied answers."""

import argparse
from collections import Counter, defaultdict
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from code.data import load_csv, SCHEMAS
from code.evidence import load_evidence_files
from code.main import predict
from code.validation import read_output, validate_output_rows

STEP_FIELDS = ("step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id")


def _step_mismatch_counts(expected_steps: list[dict], actual_steps: list[dict]) -> dict:
    """Compare phase steps separately from distinct resource IDs."""
    expected_resources = {
        (step.get("system_id"), step.get("resource_id")) for step in expected_steps
    }
    actual_resources = {
        (step.get("system_id"), step.get("resource_id")) for step in actual_steps
    }
    expected_groups = defaultdict(list)
    actual_groups = defaultdict(list)
    for step in expected_steps:
        expected_groups[(step.get("phase"), step.get("system_id"), step.get("resource_id"))].append(step)
    for step in actual_steps:
        actual_groups[(step.get("phase"), step.get("system_id"), step.get("resource_id"))].append(step)

    missing_steps = extra_steps = operation_or_state_fields = wrong_evidence_references = 0
    for key in expected_groups.keys() | actual_groups.keys():
        expected_group, actual_group = expected_groups[key], actual_groups[key]
        missing_steps += max(0, len(expected_group) - len(actual_group))
        extra_steps += max(0, len(actual_group) - len(expected_group))
        for expected_step, actual_step in zip(expected_group, actual_group):
            operation_or_state_fields += sum(
                expected_step.get(field) != actual_step.get(field)
                for field in ("operation", "state")
            )
            wrong_evidence_references += (
                expected_step.get("evidence_id") != actual_step.get("evidence_id")
            )

    def without_step_no(step):
        return tuple(step.get(field) for field in STEP_FIELDS[1:])

    expected_order = [without_step_no(step) for step in expected_steps]
    actual_order = [without_step_no(step) for step in actual_steps]
    ordering_only = expected_order != actual_order and Counter(expected_order) == Counter(actual_order)
    return {
        "missing_resources": len(expected_resources - actual_resources),
        "extra_resources": len(actual_resources - expected_resources),
        "missing_steps": missing_steps,
        "extra_steps": extra_steps,
        "operation_or_state_fields": operation_or_state_fields,
        "wrong_evidence_references": wrong_evidence_references,
        "ordering_only": ordering_only,
    }


def _resource_sources(resource_id: str, audit_at: str, evidence, manifest, activities) -> str:
    """Summarize participant-facing source hits without treating activity as proof."""
    sources = []
    seen = set()
    for record in evidence:
        if record.get("resource_id") != resource_id:
            continue
        file_id = record.get("file_id", "")
        captured_at = manifest.get(file_id, "")
        observed_at = record.get("observed_at", "")
        marker = f"{file_id}@capture:{captured_at}/observed:{observed_at}"
        if captured_at > audit_at:
            marker += " [post-audit capture; excluded]"
        if marker not in seen:
            sources.append(marker)
            seen.add(marker)
    for activity in activities:
        if activity.get("resource_id") != resource_id:
            continue
        marker = (
            f"{activity.get('activity_id')}@{activity.get('event_time')} "
            f"{activity.get('event_type')} result={activity.get('reported_result')} [claim]"
        )
        if marker not in seen:
            sources.append(marker)
            seen.add(marker)
    return "; ".join(sources) if sources else "no literal resource hit in participant evidence/activity"


def evaluate(prediction_path: Path | None = None) -> dict:
    dataset_dir = REPO_ROOT / "dataset"
    sample_requests = load_csv(dataset_dir / "sample_deletion_requests.csv", SCHEMAS["sample_deletion_requests.csv"])
    expected_path = dataset_dir / "sample_output.csv"
    expected = load_csv(expected_path, ("case_id", "deletion_status", "steps_json"))
    manifest_rows = load_csv(dataset_dir / "evidence_files.csv", SCHEMAS["evidence_files.csv"])
    manifest_times = {row["file_id"]: row["captured_at"] for row in manifest_rows}
    evidence_records = load_evidence_files(dataset_dir, manifest_rows)
    activities = load_csv(dataset_dir / "system_activity.csv", SCHEMAS["system_activity.csv"])
    request_by_id = {row["case_id"]: row for row in sample_requests}
    if prediction_path is None:
        actual = predict(dataset_dir, "sample_requests")
        prediction_label = "in-memory sample prediction"
    else:
        actual = read_output(prediction_path)
        prediction_label = str(prediction_path)
    validate_output_rows(
        actual, [row["case_id"] for row in sample_requests],
        set(manifest_times),
        {row["case_id"]: row["audit_at"] for row in sample_requests},
        manifest_times,
    )
    actual_by_id = {row["case_id"]: row for row in actual}
    expected_by_id = {row["case_id"]: row for row in expected}
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError("prediction and sample answer case IDs differ")

    statuses_correct = 0
    step_count_correct = 0
    sequences_correct = 0
    total_fields = field_correct = 0
    mismatches = []
    resource_comparisons = []
    matrix = {
        "classification_cases": 0,
        "missing_resources": 0,
        "extra_resources": 0,
        "missing_steps": 0,
        "extra_steps": 0,
        "operation_or_state_fields": 0,
        "wrong_evidence_references": 0,
        "ordering_only_cases": 0,
    }
    for case_id in sorted(expected_by_id):
        expected_row, actual_row = expected_by_id[case_id], actual_by_id[case_id]
        exp_steps, act_steps = json.loads(expected_row["steps_json"]), json.loads(actual_row["steps_json"])
        fields = []
        if actual_row["deletion_status"] == expected_row["deletion_status"]:
            statuses_correct += 1
        else:
            matrix["classification_cases"] += 1
            fields.append(f"deletion_status expected={expected_row['deletion_status']} actual={actual_row['deletion_status']}")
        if len(act_steps) == len(exp_steps):
            step_count_correct += 1
        else:
            fields.append(f"step_count expected={len(exp_steps)} actual={len(act_steps)}")
        if act_steps == exp_steps:
            sequences_correct += 1
        expected_by_resource = {(s.get("system_id"), s.get("resource_id")): s for s in exp_steps}
        actual_by_resource = {(s.get("system_id"), s.get("resource_id")): s for s in act_steps}
        missing_resources = sorted(expected_by_resource.keys() - actual_by_resource.keys())
        extra_resources = sorted(actual_by_resource.keys() - expected_by_resource.keys())
        step_counts = _step_mismatch_counts(exp_steps, act_steps)
        for key in ("missing_resources", "extra_resources", "missing_steps", "extra_steps"):
            matrix[key] += step_counts[key]
        matrix["operation_or_state_fields"] += step_counts["operation_or_state_fields"]
        matrix["wrong_evidence_references"] += step_counts["wrong_evidence_references"]
        matrix["ordering_only_cases"] += step_counts["ordering_only"]
        if missing_resources or extra_resources or exp_steps != act_steps or actual_row["deletion_status"] != expected_row["deletion_status"]:
            audit_at = request_by_id[case_id]["audit_at"]
            resource_comparisons.append({
                "case_id": case_id,
                "expected": sorted(expected_by_resource),
                "predicted": sorted(actual_by_resource),
                "missing": [
                    (system_id, resource_id, _resource_sources(resource_id, audit_at, evidence_records, manifest_times, activities))
                    for system_id, resource_id in missing_resources
                ],
                "extra": [
                    (system_id, resource_id, _resource_sources(resource_id, audit_at, evidence_records, manifest_times, activities))
                    for system_id, resource_id in extra_resources
                ],
            })
        max_steps = max(len(exp_steps), len(act_steps))
        for index in range(max_steps):
            if index >= len(exp_steps):
                fields.append(f"step[{index + 1}] unexpected actual={act_steps[index]}")
                continue
            if index >= len(act_steps):
                fields.append(f"step[{index + 1}] missing expected={exp_steps[index]}")
                continue
            for field in STEP_FIELDS:
                total_fields += 1
                if act_steps[index].get(field) == exp_steps[index].get(field):
                    field_correct += 1
                else:
                    fields.append(f"step[{index + 1}].{field} expected={exp_steps[index].get(field)!r} actual={act_steps[index].get(field)!r}")
        if fields:
            mismatches.append({"case_id": case_id, "fields": fields})

    count = len(expected_by_id)
    return {
        "cases": count,
        "status_correct": statuses_correct,
        "status_accuracy": statuses_correct / count if count else 0.0,
        "step_count_correct": step_count_correct,
        "step_count_accuracy": step_count_correct / count if count else 0.0,
        "field_correct": field_correct,
        "field_total": total_fields,
        "field_accuracy": field_correct / total_fields if total_fields else 1.0,
        "sequence_correct": sequences_correct,
        "sequence_accuracy": sequences_correct / count if count else 0.0,
        "mismatches": mismatches,
        "mismatch_matrix": matrix,
        "resource_comparisons": resource_comparisons,
        "prediction_path": prediction_label,
    }


def write_report(result: dict) -> Path:
    report_path = REPO_ROOT / "code" / "evaluation" / "evaluation_report.md"
    lines = [
        "# Public Sample Evaluation",
        "",
        "Generated by `python code/evaluation/main.py` using the participant-facing prediction pipeline and the supplied public sample answer file.",
        "",
        "## Metrics",
        "",
        f"- Public cases evaluated: {result['cases']}",
        f"- Deletion-status accuracy: {result['status_correct']}/{result['cases']} ({result['status_accuracy']:.2%})",
        f"- Step-count accuracy: {result['step_count_correct']}/{result['cases']} ({result['step_count_accuracy']:.2%})",
        f"- Aligned step-field accuracy: {result['field_correct']}/{result['field_total']} ({result['field_accuracy']:.2%})",
        f"- Exact ordered step-sequence accuracy: {result['sequence_correct']}/{result['cases']} ({result['sequence_accuracy']:.2%})",
        "",
        "Field accuracy compares the seven required fields at matching step indices. Missing/extra steps are reported separately by step-count and sequence accuracy.",
        "",
        "## Evaluator Diagnostic Correction",
        "",
        "The previous mismatch matrix labeled unique missing/extra `(system_id, resource_id)` pairs as missing/extra steps and collapsed repeated phases for a resource during field diagnostics. It now reports distinct resource counts separately from missing/extra `(phase, system_id, resource_id)` steps and compares operation/state/evidence per aligned phase step. On this sample set, the corrected values are 29 missing resources and 29 missing phase steps, plus one extra resource and one extra phase step. The headline accuracy metrics are unchanged.",
        "",
        "## Mismatch Matrix",
        "",
        "Resource counts use distinct `(system_id, resource_id)` pairs. Phase-step counts use `(phase, system_id, resource_id)` groups, so a missing phase is counted even when another step for that resource exists. Field accuracy compares seven fields at matching array indices; missing/extra array tails are covered by the step-count metric.",
        "",
        f"- Classification mismatches: {result['mismatch_matrix']['classification_cases']} cases",
        f"- Missing resources: {result['mismatch_matrix']['missing_resources']}",
        f"- Extra resources: {result['mismatch_matrix']['extra_resources']}",
        f"- Missing phase steps: {result['mismatch_matrix']['missing_steps']}",
        f"- Extra phase steps: {result['mismatch_matrix']['extra_steps']}",
        f"- Wrong operation/state fields: {result['mismatch_matrix']['operation_or_state_fields']}",
        f"- Wrong evidence references: {result['mismatch_matrix']['wrong_evidence_references']}",
        f"- Ordering-only mismatches: {result['mismatch_matrix']['ordering_only_cases']} cases",
        "",
        "## Resource-Level Table",
        "",
        "Resources are keyed by `(system_id, resource_id)`. Evidence sources include manifest capture and record observation timestamps. Activity entries are claims, not proof. Post-audit captures are listed but excluded.",
        "",
        "| Case | Expected resources | Predicted resources | Missing resources and source hits | Extra resources and source hits |",
        "|---|---|---|---|---|",
    ]
    for row in result["resource_comparisons"]:
        expected_cell = "<br>".join(f"{system}/{resource}" for system, resource in row["expected"]) or "-"
        predicted_cell = "<br>".join(f"{system}/{resource}" for system, resource in row["predicted"]) or "-"
        missing_cell = "<br>".join(
            f"{system}/{resource}: {sources}" for system, resource, sources in row["missing"]
        ) or "-"
        extra_cell = "<br>".join(
            f"{system}/{resource}: {sources}" for system, resource, sources in row["extra"]
        ) or "-"
        lines.append(f"| {row['case_id']} | {expected_cell} | {predicted_cell} | {missing_cell} | {extra_cell} |")
    lines.extend([
        "",
        "## Source Review Findings",
        "",
        "- The current/historical identity files were checked for the sample subjects; exact names, emails, phones, hashes, stable user IDs, and explicit aliases were used where present. No missing resource was linked by a new universal alias pattern.",
        "- Several account rows in evidence_92 are 404 lookups with no lookup key or subject field; resource IDs alone do not identify the requester. Its capture time is 2026-09-15T11:44:55Z, before the noon audits, so its state is eligible but the subject association is not established.",
        "- Several analytics rows in evidence_92 contain only null identity fields and cohort/metric data. Nearby rows in a global export do not establish that they concern the same person.",
        "- Evidence_02 has later snapshots with some matching user/resource associations, but its manifest capture is 2026-09-17T12:00:00Z, after the relevant 2026-09-15 audits; those records are excluded even where an embedded snapshot time is earlier.",
        "- The participant PDFs were text-extracted and the screenshots were visually reviewed. They provided no additional identity link for the missing resources. The deleted-account reference screenshot identifies user_17 but does not name account_6523.",
        "- Case_04 has no participant-facing occurrence of account_004. Its analytics_901 row in evidence_56 (captured 2026-09-07T09:45:00Z) has null user/email/phone/hash fields. Activity_3463 at 2026-08-27T08:47:41Z is a nearby anonymization claim, but does not identify a subject. No current or historical identity, hash, stable user reference, SQL row, PDF, screenshot, log, or JSON field supplies the missing account link.",
        "",
        "## Additional Contract Scenarios",
        "",
        "These participant-authored tests are in `code/tests/test_validation.py`:",
        "",
        "1. Non-deletion access request produces `NOT_APPLICABLE` with no steps.",
        "2. An incomplete finding that cites an evidence ID outside the manifest is rejected.",
        "3. A `COMPLETE` prediction containing remediation rather than evidence-backed verification is rejected.",
        "",
        "## Failures and Improvements",
        "",
        "- Integrated existing identity, authorization, evidence, state, policy, and planner modules into a deterministic prediction pipeline.",
        "- Added output validation for exact columns, row IDs/order, JSON arrays, field sets, allowed operations/states, phase/operation ordering, and provenance references.",
        "- Corrected log-start records being treated as proof of resource presence; added SQL table system inference and canonical service aliases.",
        "- Added text matching for participant names in documents, log trace correlation for lookup keys, and policy handling for explicit active/identifiable states and hashed correlation keys.",
        "- Remaining mismatches show incomplete resource linking and evidence interpretation; see the per-case field differences below. The current sample score is insufficient to claim a reliable full-dataset submission.",
        "",
        "## Exact Mismatches",
        "",
    ])
    if not result["mismatches"]:
        lines.append("No mismatches.")
    else:
        for mismatch in result["mismatches"]:
            lines.append(f"### {mismatch['case_id']}")
            lines.append("")
            lines.extend(f"- `{field}`" for field in mismatch["fields"])
            lines.append("")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, help="use an existing CSV; otherwise generate sample predictions")
    args = parser.parse_args(argv)
    result = evaluate(args.predictions)
    report_path = write_report(result)
    print(f"Public samples: {result['cases']}")
    print(f"Status accuracy: {result['status_correct']}/{result['cases']} ({result['status_accuracy']:.2%})")
    print(f"Step-count accuracy: {result['step_count_correct']}/{result['cases']} ({result['step_count_accuracy']:.2%})")
    print(f"Field accuracy: {result['field_correct']}/{result['field_total']} ({result['field_accuracy']:.2%})")
    print(f"Sequence accuracy: {result['sequence_correct']}/{result['cases']} ({result['sequence_accuracy']:.2%})")
    print(f"Detailed report: {report_path}")
    for mismatch in result["mismatches"]:
        print(f"{mismatch['case_id']}: " + " | ".join(mismatch["fields"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
