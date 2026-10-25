# Status-Consistent Temporal Link and Wave Experiments

## Account rule

Implemented the status-consistency filter and one-to-one propagation specified in the follow-up: `COMPLETE → SUCCESS`, `NOT_STARTED → FAILED`, and `PARTIALLY_COMPLETE → PARTIAL or SUCCESS`; activity time is 0.70–1.30 hours before `reported_at`, or up to 15 minutes after it; candidate events must fall between `requested_at` and `audit_at`. A request with one remaining candidate claims that activity, which is removed from other requests' candidate sets; unique claims propagate until no further assignment is possible.

The rule supplements the previously integrated account hint. Activity still only nominates an account resource. The engine emits a step only after independent, cutoff-safe state reconstruction; complete verifications cite that state evidence. The entire 518-request plus 32-sample universe is used when resolving claims.

### Public sample results

Baseline was current `output.csv`/source, which reproduced the previously measured sample metrics. The new sample candidate changes exactly the six requested cases, adding one `VERIFY_RECORD_ABSENT` step in each and changing no other sample rows:

- case_09 → account_3960
- case_10 → account_010
- case_20 → account_5037
- case_21 → account_6440
- case_22 → account_4990
- case_27 → account_3866

| Metric | Before | After |
|---|---:|---:|
| Status accuracy | 31/32 (96.88%) | 31/32 (96.88%) |
| Step-count accuracy | 13/32 (40.62%) | 15/32 (46.88%) |
| Aligned fields | 1002/1148 (87.28%) | 1070/1190 (89.92%) |
| Exact ordered sequences | 13/32 (40.62%) | 15/32 (46.88%) |

Candidate CSV: `.accuracy-baseline/account_status_candidate_samples.csv`. The public evaluator and output validator passed.

### Full 518-row diff

Candidate CSV: `.accuracy-baseline/account_status_candidate_full.csv`. It passed the exact 518-row schema, sort, uniqueness, step, operation, evidence-reference, and cutoff validator. Compared with root `output.csv`:

- 120 rows changed; each gained exactly one account-service `VERIFY_RECORD_ABSENT` step.
- No prior step was removed.
- Three statuses changed from INCOMPLETE to COMPLETE: case_415, case_417, case_419. Each previously had no established state; the new step is supported by an independently reconstructed ABSENT state from evidence_66, captured 2026-03-10 and available before the 2026-03-25 audit cutoff. Their unique primary-profile events match the request status mapping and time window.
- Detailed row and activity references are in `account_status_full_diff.csv`.

This is a material wider-population effect, but it is bounded to one account absence verification per uniquely assigned request. The three status changes follow the engine's existing rule that an authorized request with established compliant state and no violation is COMPLETE. Root `output.csv` remains unchanged pending promotion approval.

## Analytics anonymization trial

Tested `ANONYMIZE_RECORD` events targeting `analytics_platform` using the same status mapping and global candidate exclusion. The account timing window produced zero eligible assignments. The public target events cluster about 28–29 minutes before `reported_at`, outside that window. A diagnostic 20–40-minute-before window found analytics activity candidates, but exact target events overlapped 2–6 request windows apiece for six of the seven missing sample resources, so global one-to-one uniqueness rejected them. The remaining case's event was about six minutes before `reported_at`, outside the tested wave window. Several NOT_STARTED requests also had SUCCESS anonymization results, which fail the stated status-consistency mapping.

No analytics candidate was integrated. Assigning the clustered events would require a looser or different join than the supplied status/time rule, and would risk attaching an operation to the wrong request.

## Retained audit-record trial

The participant activity stream contains zero `RETAIN_RECORD` or `VERIFY_RECORD_PRESENT` events for `security_service` (one unrelated `LINK_RESOURCE_IDENTITY` event exists). There is no worker-event set to correlate. No audit-record rule was added; the relevant matching rows in the snapshot bundle are captured after the sample audit cutoffs.

## Checks

- `python -m unittest discover -s code/tests -v`: 67 passed, including positive/negative status mapping, timing, ambiguous claims, propagation, and independent-state coverage.
- `python code/main.py --samples --output .accuracy-baseline/account_status_candidate_samples.csv`: 32 validated rows.
- `python code/evaluation/main.py --predictions .accuracy-baseline/account_status_candidate_samples.csv`: completed with the metrics above.
- `python code/main.py --output .accuracy-baseline/account_status_candidate_full.csv`: 518 validated rows.

Root `output.csv` and `code.zip` were not modified. The current temporal-correlation heuristic still has no explicit contract-defined tolerance; its event, status, uniqueness, audit-cutoff, and independent-state gates are preserved and made more restrictive for the new account path.
