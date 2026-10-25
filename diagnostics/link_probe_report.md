# Diagnostic Link Probe

`link_probe.py` was absent when searched for. This diagnostic-only script uses participant-facing identity, activity, manifest, and evidence data to generate candidate resources. It does not write production predictions. `sample_output.csv` and `per_case_misses.csv` are loaded only after candidate generation for scoring.

## Candidate techniques

- `trace_current`: explicit current requester identifier in one eligible evidence record and a separate resource-bearing record sharing the same file-local `trace_id`; no time-proximity joins.
- `trace_history`: same trace rule, allowing historical identifiers and stable user_id as the explicit identity edge.
- `json_record_current`: exact identifier match inside one eligible parsed JSON record; sibling records in the enclosing bundle are never cross-joined.
- `history_record`: exact match against user_audit_log old/new identifiers available by the request cutoff, plus the stable user_id; records remain individually cutoff checked.

All candidate sources require manifest `captured_at <= audit_at` and record `observed_at <= audit_at`.

## Candidate recall and precision

Candidate precision is measured against any expected resource in that case. False candidate count is the number of candidates not present in any expected step. Missing-resource recall is exact overlap with the 29 missing phase-steps' resources.

| Technique | Candidate resources | Overlap with 29 missing resources | Missing-resource recall | Expected resources matched | Precision | Not in any expected step | Ineligible candidates |
|---|---:|---:|---:|---:|---:|---:|---:|
| trace_current | 17 | 0 | 0/29 (0.00%) | 16 | 94.12% | 1 | 0 |
| trace_history | 18 | 0 | 0/29 (0.00%) | 17 | 94.44% | 1 | 0 |
| json_record_current | 23 | 0 | 0/29 (0.00%) | 23 | 100.00% | 0 | 0 |
| history_record | 43 | 0 | 0/29 (0.00%) | 43 | 100.00% | 0 | 0 |
| technique union | 62 | 0 | 0/29 (0.00%) | 61 | 98.39% | 1 | 0 |

## End-to-end sample metrics

- Current production baseline: status 31/32, step count 13/32, fields 1002/1148 (87.28%), sequence 13/32, missing 29, extra 1.
- Trace-correlation candidate enrichment: status 31/32, step count 13/32, fields 1002/1148 (87.28%), sequence 13/32, missing 29, extra 1.
- Trace plus history combination: status 31/32, step count 13/32, fields 1002/1148 (87.28%), sequence 13/32, missing 29, extra 1.
- Record-level nested JSON and historical identifier matching are already active in production (`find_matching_evidence` and `identifiers_for_user`), so their isolated end-to-end result is the baseline; adding them again makes no candidate change.

Newly recovered exact missing phase-steps under trace enrichment: [].
Newly recovered exact missing phase-steps under trace plus history: [].

## Full evaluation-set impact

Read-only candidate generation over all 518 requests produced 207 trace-linked resource candidates and 88 candidate enrichments. It did not modify or write output.csv. Requests with any candidate: 88.

## Candidate evidence detail

Per-candidate linkage/provenance/eligibility details are in `link_probe_candidates.csv`. Each row identifies the candidate method, source evidence IDs, capture and observation times, cutoff eligibility, and overlap with expected missing/all expected resources.

## Decision

No new production rule is justified by this probe unless a candidate adds an explicit identity edge supported by eligible participant evidence and improves exact ordered sequences without false candidates. Trace propagation is diagnostic-only here; JSON record-boundary matching and historical identity resolution already exist in production. The probe never accepts a later manifest capture because of a nested observed_at value.
