# Public Sample Evaluation

Generated with `python code/evaluation/main.py` against the participant-facing
`dataset/sample_output.csv`. The predictor does not read sample answers.

## Metrics

| Metric | Result |
|---|---:|
| Case-level deletion-status accuracy | 31/32 (96.88%) |
| Step-count accuracy | 18/32 (56.25%) |
| Aligned step-field accuracy | 1116/1211 (92.16%) |
| Exact ordered-sequence accuracy | 17/32 (53.12%) |

Field accuracy compares the seven required fields at matching step indices.
Missing or extra steps are also reflected in step-count and exact-sequence
accuracy.

## Remaining mismatches

The evaluator reports one classification mismatch, 20 missing resources and
20 missing phase steps, zero extra resources or phase steps, zero
operation/state field mismatches, one wrong evidence reference, and zero
ordering-only cases. Case_04 remains the status mismatch: eligible evidence
does not link account_004 or analytics_901 to its requester. Other missing
resources lack eligible identity links or are supported only by evidence
captured after their audit cutoff.

## Accepted account correlation

The production path uses a status-consistent primary-profile
`DELETE_RECORD` candidate: COMPLETE maps to SUCCESS, NOT_STARTED to FAILED,
and PARTIALLY_COMPLETE to PARTIAL or SUCCESS. Events fall 0.70–1.30 hours
before `reported_at`, or no more than 15 minutes after it, and are bounded by
`requested_at` and `audit_at`. Exact current/historical identity ownership
removes cross-case candidates, then unique claims propagate one-to-one across
the full request universe. Ambiguous candidates are left unassigned.

A legacy fallback also remains: one `DELETE_RECORD` candidate for
`account_service` must be within 90 minutes of `reported_at`, no earlier than
the request, and uniquely overlap one request window in the full request
universe. This threshold is a heuristic, not a contract-defined tolerance.
Neither activity path proves deletion. The engine requires independent,
cutoff-safe state reconstruction; manifest `captured_at` and record
`observed_at` must both be no later than `audit_at`. Identity-linked account
evidence observed before a request cannot support that later request.

The final full output differs from the pre-promotion baseline in 157 rows:
each adds one uniquely assigned account absence verification. Three cases
also move from INCOMPLETE to COMPLETE based on independently reconstructed
absence scopes in evidence_66. The complete row diff is
`diagnostics/final_output_diff.csv`.

## Additional participant-authored evaluation cases

1. `test_non_deletion_request_has_no_steps`: a non-deletion request is
   `NOT_APPLICABLE` with an empty step list.
2. `test_incomplete_finding_requires_manifest_evidence`: reject a finding that
   cites an evidence ID outside the manifest.
3. `test_one_to_one_hint_propagation_and_ambiguous_claims`: propagate a unique
   event claim and suppress a shared ambiguous candidate.
4. `test_pre_request_account_identity_link_cannot_support_later_state`: reject
   a stale account identity link for a later request.
5. `test_complete_requires_only_cited_verification`: reject remediation steps
   in a COMPLETE result.

## Experiments, failures, and improvements

- The status-consistent account rule improved exact sequences from 13/32 to
  15/32 and aligned fields from 1002/1148 (87.28%) to 1070/1190 (89.92%).
- Exact identity tie-breaking alone reached 16/32 exact sequences; the stale
  account-link gate alone also reached 16/32. The combined accepted version
  reaches 17/32. No previously exact sample row changed in those experiments.
- Relaxing the manifest capture-time gate to use embedded observation times
  was rejected. It changed ten sample rows, reduced status accuracy from
  31/32 to 28/32, caused regressions in cases 26–28, and gained no exact
  sequence. The production gate remains unchanged.
- A 20–40-minute analytics wave trial remained ambiguous for several target
  resources or failed status consistency. No analytics rule was integrated.
  The activity stream has no `RETAIN_RECORD` or `VERIFY_RECORD_PRESENT`
  events for `security_service`; no audit-record rule was integrated.
- Run reconstruction from evidence_67 records a March readback for
  account_6523, but it predates case_17's August request. It cannot establish
  post-request state, so the case_17 account_6523 step was removed.
- The PDFs yielded text through the repository parser; evidence_58 identifies
  support_001 and has a focused test. Eleven images were visually reviewed.
  `pdftotext` and OCR executables were unavailable; that method limitation is
  disclosed in `diagnostics/final_account_link_experiment.md`.

## What was validated and what remains uncertain

- `python -m unittest discover -s code/tests -v`: 69 tests passed.
- `python code/evaluation/main.py`: 32 public cases evaluated with the
  metrics above.
- `python code/main.py --output .accuracy-baseline/final_reproduction.csv`:
  the official output validator accepted all 518 rows, and the reproduction
  matched root `output.csv` byte-for-byte.
- The output schema, row IDs/order, JSON steps, operation/state fields,
  evidence references, and capture/audit cutoffs were validated.

Deterministic reproduction and passing tests do not establish hidden-answer
accuracy. Exact sequence accuracy remains 17/32; ambiguous account candidates
are intentionally omitted, and the unlinked case_04 resources remain
unresolved.
