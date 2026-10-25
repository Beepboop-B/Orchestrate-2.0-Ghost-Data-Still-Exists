# Final Account-Link Experiments

## Request-time gate

For cases 415, 417, and 419, each candidate account absence is supported by
the `customer_profiles` scope record in evidence_66. The request, cutoff, and
provenance times are:

| Case | Resource | requested_at | audit_at | evidence_66 captured_at | record observed_at | Result |
|---|---|---|---|---|---|---|
| case_415 | account_9975 | 2026-03-02T09:00:00Z | 2026-03-25T09:00:00Z | 2026-03-10T05:38:48Z | 2026-03-10T05:38:48Z | survives |
| case_417 | account_4921 | 2026-02-28T09:00:00Z | 2026-03-25T09:00:00Z | 2026-03-10T05:38:48Z | 2026-03-10T05:38:48Z | survives |
| case_419 | account_1966 | 2026-02-26T09:00:00Z | 2026-03-25T09:00:00Z | 2026-03-10T05:38:48Z | 2026-03-10T05:38:48Z | survives |

All three state observations are after their requests and before both the audit
cutoff and the manifest availability cutoff. All three flips survive.

Case_17 requests deletion on 2026-08-19. Its exact account_6523 identity link
and 404 readback in evidence_67 were observed/captured on 2026-03-10, before
that request. The engine now rejects an account identity link observed before
`requested_at`, even when a later generic scope can establish state for that
resource. This removes the unsupported account_6523 step; account_4092 remains.
The same rule preserves case_46's account_6523 link because that request was
submitted before the evidence_67 observation.

## Unique account claims

Every one of the 120 account steps added by the status-consistency candidate
maps to one uniquely assigned event after the status filter and one-to-one
propagation; zero of 120 were ambiguous. After the exact-identity tie-break,
the final candidate adds 157 account checks relative to the prior root output.
All 157 map to unique status-consistent activity hints and still require
independent cutoff-safe state reconstruction. No ambiguous candidate is
guessed. The full diff is in `final_output_diff.csv`.

## Exact-identity tie-break

The tie-break uses exact current/historical email and stable user-ID matches,
plus historical phone and email-hash identifiers from the identity audit log.
It excludes name-only matches, current phone/hash values, broad trace
correlation, and time proximity. Plain-text identifiers must be
boundary-delimited exact matches. Ownership is calculated against the entire
518-request plus 32-sample universe and the status/time candidate propagation
is rerun afterward.

Measured progression:

| Candidate | Status | Step count | Aligned fields | Exact ordered sequences |
|---|---:|---:|---:|---:|
| Before account rule | 31/32 | 13/32 | 1002/1148 (87.28%) | 13/32 |
| Status-consistent account rule | 31/32 | 15/32 | 1070/1190 (89.92%) | 15/32 |
| Exact-identity tie-break alone | 31/32 | 17/32 | 1108/1211 (91.49%) | 16/32 |
| Final with stale-link gate | 31/32 | 18/32 | 1116/1211 (92.16%) | 17/32 |

No sample row that was already exact under the status-consistent baseline
changed. The exact-identity experiment improved the score and all its changed
full-set rows add a uniquely assigned account absence check. The stale-link
gate separately removes case_17's unsupported step and makes case_17 exact.
Candidate outputs for the separate stale-link experiment are in
`.accuracy-baseline/stale_link_only_samples.csv` and
`.accuracy-baseline/stale_link_only_full.csv`.

## Analytics and retained audit records

No analytics anonymization rule was added: the candidate events are identity-
free or overlap multiple request windows, and no candidate passes the supplied
status-consistency mapping plus unique one-to-one assignment. The activity
stream contains no `RETAIN_RECORD` or `VERIFY_RECORD_PRESENT` events for
`security_service`; no audit-record wave rule was added.

## Evidence review and checks

All 94 manifest files are parsed into provenance-bearing records. The four
PDFs have extracted text; evidence_58 names support_001 and is matched by the
case_07 subject-name test. Eleven images were visually reviewed in the earlier
evidence pass; no eligible new identity edge was found. The runtime has no
`pdftotext` or OCR executable, so the PDFs used the repository's text-stream
extractor and images used visual review rather than OCR.

- Unit tests: 69 passed.
- Public sample candidate: 32 rows passed validation and evaluation.
- Full candidate: 518 rows passed output validation.
- Compared with root `output.csv`: 157 rows changed, each adding exactly one
  unique account-service absence verification; no step was removed. Cases
  415, 417, and 419 also change from INCOMPLETE to COMPLETE based on evidence_66.
