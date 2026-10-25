# Seven Evidence/State Divergences

Scope: exactly the seven `pipeline_diagnostic.csv` rows whose first divergence is `Evidence/state`. Each request's email resolves to a stable user ID. The *account resource-to-user relationship* does not: no participant evidence record names the resource, and each activity row contains only operation target data. I did not infer ownership from timing.

## Per-row trace

| Case / resource | Resolved requester | State source at cutoff | Matching activity claim | Pipeline path and loss |
|---|---|---|---|---|
| case_10 / `account_010` | user_10 | evidence_93, `evidence/databases/customer_data_inventory_20260916.sql`, capture 2026-09-16T08:37:39Z; account-service/customer_profiles scope is eligible. No resource-specific row. State reconstruction for this ID returns ABSENT from the scope. | activity_3595, 2026-09-02T10:08:37Z, DELETE_RECORD/SUCCESS; details name the target only. Request reported_at is 10:08:00Z. | SQL parser yields global scope, not an owner edge. `_matches_raw` has no resource record to link. `find_account_resource_hint` returns None because several account DELETE events fall within its 90-minute candidate window. The engine never inserts this account into `candidates`; despite hypothetical ABSENT/DELETE yielding `VERIFY_RECORD_ABSENT`, policy and planner do not process it. |
| case_18 / `account_5521` | user_50 | evidence_93, same inventory file/capture; eligible account-service scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3732, 2026-09-09T09:52:26Z, DELETE_RECORD/SUCCESS; details say primary profile target only. Request reported_at 11:00:00Z. | No resource evidence or identity field. Account hint is None: multiple account DELETE events are within 90 minutes. The resource is omitted before policy/planning. |
| case_20 / `account_5037` | user_48 | evidence_93, same inventory file/capture; eligible scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3734, 2026-09-09T10:14:55Z, DELETE_RECORD/FAILED; details name the target only. Request reported_at 11:00:00Z. | No resource evidence or identity field. Account hint is None with multiple nearby account DELETE candidates. A FAILED claim does not prove current record state or requester ownership. Omitted before policy/planning. |
| case_22 / `account_4990` | user_51 | evidence_93, same inventory file/capture; eligible scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3573, 2026-09-01T09:12:11Z, DELETE_RECORD/SUCCESS; details name the target only. Request reported_at 10:00:00Z. | No resource evidence or identity field. Account hint is None because multiple candidates are within 90 minutes. Omitted before policy/planning. |
| case_23 / `account_410` | user_23 | evidence_90, `evidence/databases/customer_data_inventory_20260905.sql`, capture 2026-09-05T07:18:01Z; eligible account-service scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3662, 2026-09-05T11:10:55Z, DELETE_RECORD/FAILED; details name the target only. Request reported_at 12:00:00Z. | No resource evidence or identity field. Account hint is None with multiple nearby account DELETE candidates. Omitted before policy/planning. |
| case_29 / `account_7012` | user_29 | evidence_90, same inventory file/capture; eligible scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3532, 2026-08-30T11:06:57Z, DELETE_RECORD/FAILED; details name the target only. Request reported_at 12:00:00Z. | No resource evidence or identity field. Account hint is None with multiple nearby account DELETE candidates. Omitted before policy/planning. |
| case_32 / `account_8858` | user_542 | evidence_90, same inventory file/capture; eligible scope, no resource-specific row. Reconstructed state is ABSENT from scope. | activity_3685, 2026-09-06T11:05:15Z, DELETE_RECORD/PARTIAL; details name the target only. Request reported_at 12:00:00Z. | No resource evidence or identity field. Account hint is None with multiple nearby account DELETE candidates. Omitted before policy/planning. |

All seven activity details fail exact matching against their resolved requester's identifiers. The scope records are global inventories; they can establish absence for a *known* account resource, but cannot establish that these activity targets belong to the requester. Activity results are claims, not state evidence.

## Comparison with passing examples

- case_03 `account_7566`, case_12 `account_9797`, case_17 `account_4092`, and case_19 `account_9102` use the same account lookup log format. Their completed rows have an explicit `lookup_key` matching the requester's known email, plus `rows=0`/`http_status=404`. Identity linking succeeds, state reconstruction returns ABSENT from the direct read, and the engine emits verification.
- case_11 `account_4248` has a parsed `NOT_FOUND` observation with `subject_reference` matching the requester; it also passes the identity gate before state and policy.
- The seven misses instead have only `system_activity.csv` target IDs and global snapshot scope. The difference is an explicit subject edge and direct resource observation in passing records, both absent here.

## Candidate ranking

| Rank | Candidate rule | Potential coverage | False-positive risk | Decision |
|---:|---|---:|---|---|
| 1 | Narrow the unique-nearby account event window; case_10's event is 37 seconds after reported_at. | At most case_10 from the observed seven; the other target events are 45?68 minutes from reported_at and share the batch with other account events. | **Disallowed/high.** It would infer resource ownership from time alone. | Reject; violates identity constraint. |
| 2 | Pair any activity target ID with account-service scope absence. | Could produce all seven expected absence checks. | **High.** The activity stream is global; no row identifies the requester, and scope is global. It would turn unrelated deletion operations into user records. | Reject; scope proves state only after resource ownership is known. |
| 3 | Trust SUCCESS/FAILED/PARTIAL activity results as current state. | Could add steps for several targets. | **High and contract-invalid.** Results are claims, can be stale, and do not establish ownership. | Reject. |

## Result

No state transition defect explains these seven omissions. State reconstruction consistently returns ABSENT from eligible global scopes, and USER_PROFILE policy requires DELETE; the records are lost earlier because no resource-to-requester edge exists and the account hint is ambiguous. No candidate satisfies the explicit identity requirement, so no production rule or prediction change is justified. Existing tests already cover direct 404 observations and refusal of ambiguous activity-time links; no new test was added for a rejected rule.
