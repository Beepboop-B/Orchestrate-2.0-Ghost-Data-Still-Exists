# Per-case missing phase-step analysis

Generated from the public evaluator's expected-vs-predicted phase-step comparison. `sample_output.csv` is used only as evaluation ground truth; production predictions come from `code.main.predict` and do not load it.

## Bucket definitions

Each missing phase-step has one primary cause at the first failed production gate:

- `identity_not_linked`: a resource ID is present in a source/claim, but the evidence does not establish that it belongs to the resolved requester. This includes activity-only targets and source records with empty identity/correlation fields.
- `source_data_never_extracted`: no usable participant source establishes that resource/state by the cutoff. This includes source records absent from participant evidence and captures excluded because they were collected after `audit_at`.
- `policy_or_state_decided_nothing_to_do`: an identity-linked, state-bearing candidate reached policy, but policy/state omitted a required step.
- `planner_dropped_step`: a required finding/remediation/verification was produced upstream but omitted by serialization/planning.

The extra prediction is reported separately as `extra_candidate_attribution`; its expected fields are blank in the CSV because no expected phase-step exists.

## Reconciliation and counts

| Primary reason | Missing phase-steps |
|---|---:|
| `identity_not_linked` | 19 |
| `source_data_never_extracted` | 10 |
| `policy_or_state_decided_nothing_to_do` | 0 |
| `planner_dropped_step` | 0 |
| **Total missing** | **29** |

The evaluator also reports one extra phase-step (`extra_candidate_attribution`), so `per_case_misses.csv` has 30 data rows. This reconciles to the evaluator's 29 missing and one extra phase-step counts. It reports 29 distinct missing resources as well because every missing resource in this sample has one missing phase-step.

### First-divergence mapping

The 19 identity-link misses comprise 12 `Identity join` rows and seven `Evidence/state` rows. In the latter, a resource target occurs in global activity, but the activity does not identify the requester and is not resulting-state evidence. The 10 source-data misses comprise six `Audit cutoff`, one `Resource identification`, two `Participant evidence`, and one `Source/evidence` rows. There are no rows whose first lost stage is policy/state or planner.

### Missing steps by case

Counts are phase-steps, not unique resources:

| Case | Missing |
|---|---:|
| case_03 | 1 |
| case_04 | 2 |
| case_09 | 2 |
| case_10 | 1 |
| case_18 | 2 |
| case_20 | 2 |
| case_21 | 2 |
| case_22 | 1 |
| case_23 | 2 |
| case_24 | 1 |
| case_25 | 2 |
| case_26 | 2 |
| case_27 | 2 |
| case_28 | 2 |
| case_29 | 2 |
| case_30 | 1 |
| case_31 | 1 |
| case_32 | 1 |

### Missing steps by system

| System | Missing |
|---|---:|
| account_service | 15 |
| analytics_platform | 7 |
| security_service | 7 |

## Highest-count bucket and candidate rule

The highest-count bucket is `identity_not_linked` (19). A representative failing case is case_21: evidence_92's eligible account lookup names `account_6440` and returns 404, but the lookup row has no requester key; its analytics row has null identity fields. Compare the passing direct lookup for case_12 in `service_events_ap_south_20260915.log`: the completed `account_9797` lookup is connected to a `lookup_key` equal to the requester's email. The direct result and explicit identity key support the step; the case_21 resource ID plus 404 alone does not.

The proposed general rule was to enumerate candidate resource membership from evidence linked by explicit current/historical identifiers, independently of state confidence, and let state choose any justified treatment. This is already how `code/engine.py` works: it builds `candidates` from `find_matching_evidence` before calling `reconstruct_resource_state`. An identity history row alone contains no system/resource membership, and global activity/scope cannot supply that owner edge. In a read-only pass over all 518 requests, 478 had 1,042 explicitly identity-linked resource candidates; 22 candidates across 15 requests had no reconstructable state. The candidate-enumeration rule adds **zero cases** beyond current production behavior. None of the 29 expected missing resources had an explicit identity-linked evidence candidate in the sample pass.

Emitting a step for a candidate with unknown state would invent a finding or verification without a supported state and would violate the evidence contract. Therefore no production change or regression test was added. Policy/state mapping and planner ordering are not the dominant failure: evaluator comparisons report zero operation/state/evidence mismatches on shared phase-steps and zero ordering-only cases.

## Files

- `per_case_misses.csv`: one row for each of the 29 missing phase-steps plus one separate extra prediction row.
- `pipeline_diagnostic.csv`: per-resource source and first-divergence context.
- `code/evaluation/evaluation_report.md`: full evaluator mismatch report.
