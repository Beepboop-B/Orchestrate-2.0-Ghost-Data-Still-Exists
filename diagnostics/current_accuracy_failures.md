# Current Gated Source: Public Sample Failures

Baseline is generated from the current production engine in `.accuracy-baseline/accuracy_working_baseline.csv`. Comparison uses complete ordered phase-step signatures and LCS alignment. Shared resource/phase steps with differing operation/state/evidence are reported separately; unmatched tails/steps are classified as missing or extra. All source times are compared with both request `audit_at` and manifest capture time.

## Reproduced metrics

- Status: 31/32 (96.88%)
- Step count: 13/32 (40.62%)
- Aligned fields: 1002/1148 (87.28%)
- Exact ordered sequence: 13/32 (40.62%)
- Unit tests: 63 passed

## Non-exact cases

- case_03: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_94@capture:2026-09-26T10:38:56Z/observed:2026-09-26T09:54:09Z; activity_3852@2026-09-15T10:31:16Z ANONYMIZE_RECORD result=SUCCESS [claim].
- case_04: expected COMPLETE, predicted INCOMPLETE; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: no literal resource hit in participant evidence/activity.
- case_09: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_06@capture:2026-09-18T11:55:24Z/observed:2026-09-16T08:57:34Z [post-audit capture; excluded]; activity_3703@2026-09-07T07:55:18Z DELETE_RECORD result=FAILED [claim].
- case_10: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3595@2026-09-02T10:08:37Z DELETE_RECORD result=SUCCESS [claim].
- case_17: status matches; 0 missing phase-steps, 1 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_67@capture:2026-03-10T06:18:01Z/observed:2026-03-10T06:18:01Z; activity_3850@2026-09-15T09:56:51Z DELETE_RECORD result=SUCCESS [claim].
- case_18: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3732@2026-09-09T09:52:26Z DELETE_RECORD result=SUCCESS [claim].
- case_20: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3734@2026-09-09T10:14:55Z DELETE_RECORD result=FAILED [claim].
- case_21: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_92@capture:2026-09-15T11:44:55Z/observed:2026-09-15T09:31:19Z; activity_3661@2026-09-05T11:01:53Z DELETE_RECORD result=SUCCESS [claim].
- case_22: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3573@2026-09-01T09:12:11Z DELETE_RECORD result=SUCCESS [claim].
- case_23: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3662@2026-09-05T11:10:55Z DELETE_RECORD result=FAILED [claim].
- case_24: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_02@capture:2026-09-17T12:00:00Z/observed:2026-09-15T12:00:00Z [post-audit capture; excluded].
- case_25: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_92@capture:2026-09-15T11:44:55Z/observed:2026-09-15T09:31:40Z; activity_3597@2026-09-02T10:48:27Z DELETE_RECORD result=FAILED [claim].
- case_26: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_02@capture:2026-09-17T12:00:00Z/observed:2026-09-09T12:00:00Z [post-audit capture; excluded]; evidence_92@capture:2026-09-15T11:44:55Z/observed:2026-09-15T09:01:48Z; activity_3600@2026-09-02T11:08:43Z DELETE_RECORD result=FAILED [claim].
- case_27: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_02@capture:2026-09-17T12:00:00Z/observed:2026-09-17T12:00:00Z [post-audit capture; excluded]; evidence_92@capture:2026-09-15T11:44:55Z/observed:2026-09-15T09:59:48Z; activity_3530@2026-08-30T10:57:28Z DELETE_RECORD result=SUCCESS [claim].
- case_28: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_92@capture:2026-09-15T11:44:55Z/observed:2026-09-15T11:07:16Z; activity_3529@2026-08-30T10:46:13Z DELETE_RECORD result=FAILED [claim].
- case_29: status matches; 2 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3532@2026-08-30T11:06:57Z DELETE_RECORD result=FAILED [claim].
- case_30: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: evidence_02@capture:2026-09-17T12:00:00Z/observed:2026-09-15T12:00:00Z [post-audit capture; excluded].
- case_31: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3682@2026-09-06T10:45:58Z DELETE_RECORD result=SUCCESS [claim].
- case_32: status matches; 1 missing phase-steps, 0 extra phase-steps, 0 shared-resource field mismatch(es). First discrepancy source: activity_3685@2026-09-06T11:05:15Z DELETE_RECORD result=PARTIAL [claim].

## Stage and rule assessment

The dominant errors happen before policy/planning: resource candidate generation cannot include a target unless eligible evidence links that resource to the resolved subject, or the unique gated account activity hint applies. Several requested targets occur only in activity claims; some state snapshots are global scopes without a resource-owner edge; several later snapshots were captured after `audit_at`. State changes on already linked resources (notably cases 09, 17, 18, 20, 22, 27, 28, 29, 30, 31, 32) are represented in `shared_target_field_mismatches` or ordering alignment in the CSV and arise in state reconstruction, policy mapping, or plan construction.

The largest repeated group is the verification-only targets (account absence, analytics anonymization, retained security records). Prior source reviews in `diagnostics/verification_semantics.md` and `diagnostics/rule_candidates.md` established these are either unlinked, only supported by claims, or available only from post-cutoff captures. The contract allows empty evidence IDs for future checks, but still requires a grounded resource and applicable remediation/retention basis. A policy category does not identify a person?s resource. No defensible broad candidate emerged for case_04 without inventing an identity relationship.

## Candidate rules reviewed

1. **State-only analytics read completion as PRESENT.** Candidate source: evidence_94 completed read with `audience_cohort=general_shopper` but null identity fields. It does not help candidate generation, lacks a requester link, and previously measured zero prediction delta.
2. **Use global account 404/profile lookup rows for the request.** evidence_92 has resource/status but empty lookup and subject fields. Linking it would not be requester-specific; reject.
3. **Promote null-identity analytics/security inventory rows using policy and timestamps.** evidence_92/evidence_02 lacks the subject link in eligible records; evidence_02 is post-cutoff for relevant cases. Grouping by adjacency, time, suffix, or category would create unsupported associations. Reject.

The integrated temporal correlation remains guarded by unique activity, unique request-window, explicit DELETE_RECORD/account_service/resource, requested_at-to-audit_at, and independently reconstructed ABSENT state gates. The 90-minute tolerance is heuristic and not contract-defined. It is unchanged.

## Outcome

No new production rule passed contract and measurement review. No candidate implementation or sample-specific lookup was added. Consequently, no full 518-row candidate regression run was warranted. Baseline outputs and protected root artifacts were not promoted or rewritten by this analysis. See CSV for each failure?s complete sequences, alignment, source hits and timestamps.
