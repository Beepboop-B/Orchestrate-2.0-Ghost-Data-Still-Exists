# Evidence Graph and Cutoff Review

This is a debugging graph built from participant-facing records. Sample answer `evidence_id` values were used only to locate corresponding sources; the production predictor does not read sample answers. Edges below come from explicit identifiers/fields, not timestamp proximity.

## Edge rules checked

- Identity snapshot and audit-history rows connect stable user IDs with current/historical identifiers.
- Structured resource rows connect an explicit resource ID to fields such as `customer_reference`, `user_id`, email/hash, or phone when populated.
- `LINK_RESOURCE_IDENTITY` activity details explicitly name a resource and stable user reference; they provide an asserted linkage edge. The activity result itself is still a claim, not state proof.
- Logs can connect records with a shared explicit trace ID. This proves only that the records belong to the same trace; a user edge still needs an identity-bearing field on that trace.
- Resource/system aliases and normalization are applied only when documented or exact (casefolded strings; digit-normalized phone). No case ID, suffix arithmetic, or timestamp-only edge is used.

## Explicit catalog edges

The activity file has 12 `LINK_RESOURCE_IDENTITY` rows. None names any of the 29 missing expected resource IDs. These edges may help find other records, but cannot recover the current missing set by themselves.

| Activity | Time | System | Resource | Stable user edge |
|---|---|---|---|---|
| activity_4000 | 2026-09-26T11:07:01Z | account_service | `account_5762` | `user_11` |
| activity_4001 | 2026-09-01T06:07:01Z | search_service | `search_428` | `user_13` |
| activity_4002 | 2026-08-07T08:07:01Z | integration_service | `data_flow_1121` | `user_14` |
| activity_4003 | 2026-07-13T10:07:01Z | analytics_platform | `analytics_7438` | `user_20` |
| activity_4004 | 2026-06-18T12:07:01Z | export_service | `export_1260` | `user_18` |
| activity_4005 | 2026-05-24T07:07:01Z | support_platform | `support_1034` | `user_22` |
| activity_4006 | 2026-04-29T09:07:01Z | backup_service | `backup_9287` | `user_16` |
| activity_4007 | 2026-02-13T08:07:01Z | object_storage | `object_19` | `user_07` |
| activity_4008 | 2026-09-16T07:27:01Z | marketing_platform | `marketing_001` | `user_09` |
| activity_4009 | 2026-07-18T11:07:01Z | export_service | `export_1842` | `user_18` |
| activity_4010 | 2026-09-05T07:07:01Z | security_service | `audit_record_003` | `user_03` |
| activity_4011 | 2026-03-10T06:07:01Z | identity_service | `tombstone_17` | `user_17` |

## Missing-resource graph findings

| Missing resource | Source node / parsed fields | Graph result |
|---|---|---|
| `analytics_9406` | evidence_94, `resource_lookup_trace_20260926_103856.log`, captured 2026-09-26T10:38:56Z; two records share trace `rb-095409-021`; lookup_key/customer_reference/email/phone/email_hash are literal null. | Trace joins started and completed events, but has no edge to the requester. |
| `account_004` | evidence_54, `customer_accounts_failover_replica_20260902.sql`, captured 2026-09-02T23:00:00Z; scoped SQL snapshot, no `account_004` row. | No resource node in source, so no identity/state edge can be formed. |
| `analytics_901` | evidence_56, `customer_analytics_report_20260907.json`, captured 2026-09-07T09:45:00Z; resource node exists; user_id/email/phone/email_hash null. | Resource node is isolated from subject identity; activity row is only an operation claim. |
| `account_6440, account_3136, account_3866, account_5482` | evidence_92, `service_resource_export_20260915_114455.json`, captured 2026-09-15T11:44:55Z; profile lookups have explicit resource IDs and 404/null profiles, no lookup or subject key. | The resource/state edge exists, but no subject edge; neighboring rows do not connect them. |
| `analytics_5335, analytics_1895, analytics_4566, analytics_4574, analytics_6077` | evidence_92, same JSON export and capture; resource IDs parse; identity fields are null. | Resource-to-subject edge is absent. Activity rows name operation targets but do not provide identity linkage. |
| `account_3960, audit_record_4902, audit_record_4128, audit_record_7095, audit_record_3954, audit_record_1707` | Exact resource hits occur only in evidence_06 or evidence_02, both captured after their respective audit_at. | No eligible exact resource record exists. Separate eligible same-system records do not name these resources. |
| `account_010, account_5521, account_5037, account_4990, account_410, account_7012, account_8858` | Only matching rows are DELETE_RECORD activity claims; no evidence-file record has the resource ID. | The resource node comes from an activity claim without an independent state edge. |
| `audit_record_6645, audit_record_5569` | No evidence-file or activity record contains these resource IDs. | No resource node or linkage path exists. |
| `account_4857` | evidence_51, `customer_data_snapshot_bundle_20260915.json`, captured 2026-09-15T12:00:00Z, contains no such resource row; activity is a delete claim. | The scoped snapshot does not identify this resource; absence cannot be established for it. |

## Six cutoff cases

The exact resource hits and audit cutoffs were checked from parsed records:

| Case / resource | Only exact resource evidence | Capture time | Cutoff | Other eligible exact source |
|---|---|---|---|---|
| case_09 / account_3960 | evidence_06 | 2026-09-18T11:55:24Z | 2026-09-16T09:00:00Z | none |
| case_09 / audit_record_4902 | evidence_06 | 2026-09-18T11:55:24Z | 2026-09-16T09:00:00Z | none |
| case_23 / audit_record_4128 | evidence_02 | 2026-09-17T12:00:00Z | 2026-09-15T12:00:00Z | none |
| case_24 / audit_record_7095 | evidence_02 | 2026-09-17T12:00:00Z | 2026-09-15T12:00:00Z | none |
| case_29 / audit_record_3954 | evidence_02 | 2026-09-17T12:00:00Z | 2026-09-15T12:00:00Z | none |
| case_30 / audit_record_1707 | evidence_02 | 2026-09-17T12:00:00Z | 2026-09-15T12:00:00Z | none |

No alternate eligible evidence item naming any of these exact resource IDs was found.

## Activity risk usage review

`system_activity.csv` contains 447 SYNC_RECORD, 1 RESTORE_BACKUP, 28 CHECK_RESTORE_ACCESS, and 89 CHECK_DATA_FLOW records. The candidate uses activity only as a candidate resource hint for a uniquely nearby account delete; evidence records establish state. The sync/restore activity details contain no explicit user/email tokens to link them to sample requesters. `LINK_RESOURCE_IDENTITY` provides explicit asserted edges but no missing-resource overlap. Treating sync/restore results as verified active state would violate the contract; no justified predictor change is supported by this activity review.

## Decision

The only confirmed defect in this turn was evaluator diagnostics: unique resource counts were mislabeled as step counts, and shared resource phases were collapsed during field mismatch classification. The evaluator now reports both resource and phase-step counts and compares operation/state/evidence by phase step. This correction changes diagnostics only; sample predictions and headline accuracy are unchanged.
