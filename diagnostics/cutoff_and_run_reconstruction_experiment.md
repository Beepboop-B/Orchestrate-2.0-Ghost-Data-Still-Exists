# Cutoff and Run Reconstruction Experiments

## Cutoff experiment

The production evidence gate remains unchanged. Both `code.audit.find_matching_evidence` and `code.state.reconstruct_resource_state` require the outer evidence file's manifest `captured_at` and the individual record's `observed_at` to be at or before `audit_at`. The official contract says later-created evidence cannot change an earlier audit. An embedded timestamp describes when a source snapshot was observed; it does not establish that the containing export was available then.

For a controlled diagnostic only, I reloaded all parsed evidence and replaced each record's `captured_at` with its `observed_at`, then regenerated all 32 samples. This intentionally ignores manifest availability and is not a valid candidate output. Compared with the valid baseline:

- 10 sample rows changed.
- Status accuracy fell from 31/32 to 28/32. Cases 26, 27, and 28 regressed from COMPLETE to INCOMPLETE; no status mismatches were fixed.
- Step-count accuracy rose from 13/32 to 18/32.
- Index-aligned field accuracy was 1035/1232 (84.01%), versus 1002/1148 (87.28%).
- Exact ordered-sequence accuracy stayed 13/32. No exact sequence was gained or lost.
- Cases 24 and 30 did not become exact. They each still had seven and fourteen steps respectively, but the candidate used post-capture evidence_02 citations for records expected to be sourced from evidence_92 and exposed other ordering/provenance differences.

This diagnostic deliberately bypasses output validation, which correctly rejects those post-capture citations. It does not justify changing the production gate.

## Source review: SQL, images, and PDFs

- **evidence_54** is `customer_accounts_failover_replica_20260902.sql`, captured 2026-09-02 23:00Z. It contains three active primary profiles for `user_8741`, `user_9116`, and `user_7204`, plus failover/replica scope metadata. It has no `account_004` row and no `user_04` record; scope cannot identify an account ID.
- **evidence_56** is a 2026-09-07 analytics report with `analytics_901`, metrics and recent activity, but null user/email/phone/hash fields. It cannot link that resource to case_04's requester.
- The participant screenshots reviewed show a customer admin record (evidence_04), search hits (09), active connector flows (14), analytics profile (19), export jobs (23), unrelated support ticket (28), archive metadata (32), signed security events for user_03 (37), a retained reference for user_17 (42), unrelated object storage files (46), and a live marketing profile (60). None supplies a new eligible identity edge for the remaining unlinked sample targets. Evidence_42 shows `user_17` and business references, but no `account_6523`.
- The PDFs parsed to text: evidence_18 is an order/customer statement for user_18; evidence_27 is a finance disputed-orders register (including user_17/user_24/user_29); evidence_55 is a signed retention extract for user_03's `audit_record_003`; evidence_58 is a delivery-address correction attachment for Priya Raman and `support_001`. These records do not identify the remaining account or null-identity analytics resources. The user_17 finance reference does not link to `account_6523`.

## Run reconstruction experiment

The strongest run-shaped source is **evidence_67**, a readback log captured 2026-03-10 06:18:01Z. Its `export_started` says `target_count=1`; a single trace `rb-061801-001` looks up `account_6523` using case_17's exact email; completion returns `rows=0` and HTTP 404; export completes with `queries=1,dropped=0`. This reconstructs a complete March readback run and gives a genuine identity edge for that resource at that time.

It still cannot establish the account's state after the deletion request, which was submitted 2026-08-19. The audit contract requires state at `audit_at` and evidence after `requested_at` to establish the deletion result. evidence_67 is more than five months earlier. Later activity_3850 (2026-09-15) names `account_6523` but has no requester identifier; the resource correlation to the request is not enough to turn the old 404 into post-request state evidence. The engine's extra verification step in case_17 is therefore not supported by an eligible state observation and remains the final separate issue, as requested.

A broad `trace_id` linkage experiment already in `diagnostics/link_probe_report.md` produced zero overlap with the 29 missing sample targets. Existing evidence parsing already groups log rows by trace. No new general run-reconstruction rule improves the sample without treating historical readback as current state or joining unrelated rows.

## Decision

No production code, expected output, root `output.csv`, or `code.zip` was changed. The cutoff relaxation was measured only as an invalid diagnostic and rejected. The existing 90-minute temporal correlation rule and all its uniqueness, independent-state, and audit-cutoff safeguards remain intact. All 63 unit tests pass.
