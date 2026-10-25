# Ranked Parser and Linkage Gap Diagnostic

This report compares every missing/extra resource in the evaluator diagnostic against manifest-backed parsed records and the source files. Public sample labels were used only to select the mismatch set. Production predictions were not changed.

## Ranked candidate defects

| Rank / defect | Missing resources explained | Manifest source(s) and capture time | Evidence finding |
|---|---:|---|---|
| 1 ? Identityless or unkeyed structured records | 12 | evidence_92 (service_resource_export_20260915_114455.json; captured 2026-09-15T11:44:55Z), evidence_94 (resource_lookup_trace_20260926_103856.log; captured 2026-09-26T10:38:56Z), evidence_56 (customer_analytics_report_20260907.json; captured 2026-09-07T09:45:00Z) | Resource IDs parse successfully, but the relevant profile fields are absent/null (404 lookup has profile=null; analytics rows contain null identifiers). This is data linkage absence, not parser loss. |
| 2 ? Post-cutoff captures | 6 | evidence_02 (customer_data_snapshot_bundle_20260917.json; captured 2026-09-17T12:00:00Z) and evidence_06 (structured_service_events_eu_west_20260918.log; captured 2026-09-18T11:55:24Z) | Relevant IDs exist in parsed captures after the applicable 2026-09-15 audit cutoff. Embedded observed times do not make later captured files eligible. No fix permitted. |
| 3 ? Operation claims without independent state records | 7 | system_activity.csv; entries name the resources but are only DELETE_RECORD/ANONYMIZE_RECORD claims. No evidence-file resource record exists for these seven IDs. | The activity stream is fully parsed, but a claim cannot establish presence/absence/anonymization state. |
| 4 ? No participant source for the resource or its state | 3 | No source record for audit_record_6645 or audit_record_5569; evidence_51 (customer_data_snapshot_bundle_20260915.json; captured 2026-09-15T12:00:00Z) does not contain account_4857. | No evidence to recover by parser or join logic; evidence_51 contains only unrelated scoped/snapshot rows for this requested resource. |
| 5 ? Resource ID absent from scoped source | 1 | evidence_54 (customer_accounts_failover_replica_20260902.sql; captured 2026-09-02T23:00:00Z) | SQL parses and establishes table/snapshot scope but contains no account_004 row/ID; cannot infer resource suffix from user_04. |
| 6 ? Image/PDF extraction gap | 0 | 11 PNG screenshots and four PDFs were reviewed; no exact missing resource ID appears in manually transcribed screenshot identifiers or extracted PDF resource IDs. | Images currently yield no OCR text, but OCR would not recover any of the 29 expected resource IDs based on the actual visible/extracted content. PDFs have text and zero embedded image objects; no OCR need. |
| 7 ? Machine parser failed or dropped explicit required identifier/state | 0 | 94/94 manifest files parsed without parser errors; exhaustive parsed-record search found no target resource occurrence omitted by the parser. | No structured parser defect supported by this sample mismatch set. |

## Per-resource source trace

The table includes every missing resource and the one extra prediction. Expected and predicted operations/states are in `pipeline_diagnostic.csv`; the source map below provides actual manifest filenames and capture timestamps.

| Kind | Case / system / resource | First divergence | Source file(s) / capture time |
|---|---|---|---|
| MISSING | case_03 / analytics_platform / `analytics_9406` | Identity join | evidence_94: `evidence/logs/resource_lookup_trace_20260926_103856.log` @ 2026-09-26T10:38:56Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_04 / account_service / `account_004` | Resource identification | evidence_54: `evidence/databases/customer_accounts_failover_replica_20260902.sql` @ 2026-09-02T23:00:00Z |
| MISSING | case_04 / analytics_platform / `analytics_901` | Identity join | evidence_56: `evidence/records/customer_analytics_report_20260907.json` @ 2026-09-07T09:45:00Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_09 / account_service / `account_3960` | Audit cutoff | evidence_06: `evidence/logs/structured_service_events_eu_west_20260918.log` @ 2026-09-18T11:55:24Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_09 / security_service / `audit_record_4902` | Audit cutoff | evidence_06: `evidence/logs/structured_service_events_eu_west_20260918.log` @ 2026-09-18T11:55:24Z |
| MISSING | case_10 / account_service / `account_010` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| EXTRA | case_17 / account_service / `account_6523` | Candidate/resource attribution | evidence_67: `evidence/logs/resource_lookup_trace_20260310_061801.log` @ 2026-03-10T06:18:01Z |
| MISSING | case_18 / account_service / `account_5521` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_18 / security_service / `audit_record_6645` | Participant evidence | No evidence file contains this resource; see the participant-source search finding in diagnostic CSV. |
| MISSING | case_20 / account_service / `account_5037` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_20 / security_service / `audit_record_5569` | Participant evidence | No evidence file contains this resource; see the participant-source search finding in diagnostic CSV. |
| MISSING | case_21 / account_service / `account_6440` | Identity join | evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_21 / analytics_platform / `analytics_5335` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_22 / account_service / `account_4990` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_23 / account_service / `account_410` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_23 / security_service / `audit_record_4128` | Audit cutoff | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z |
| MISSING | case_24 / security_service / `audit_record_7095` | Audit cutoff | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z |
| MISSING | case_25 / account_service / `account_3136` | Identity join | evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_25 / analytics_platform / `analytics_1895` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_26 / account_service / `account_5684` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_26 / analytics_platform / `analytics_4566` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_27 / account_service / `account_3866` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_27 / analytics_platform / `analytics_4574` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_28 / account_service / `account_5482` | Identity join | evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_28 / analytics_platform / `analytics_6077` | Identity join | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z; evidence_92: `evidence/records/service_resource_export_20260915_114455.json` @ 2026-09-15T11:44:55Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_29 / account_service / `account_7012` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_29 / security_service / `audit_record_3954` | Audit cutoff | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z |
| MISSING | case_30 / security_service / `audit_record_1707` | Audit cutoff | evidence_02: `evidence/records/customer_data_snapshot_bundle_20260917.json` @ 2026-09-17T12:00:00Z |
| MISSING | case_31 / account_service / `account_4857` | Source/evidence | evidence_51: `evidence/records/customer_data_snapshot_bundle_20260915.json` @ 2026-09-15T12:00:00Z; `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |
| MISSING | case_32 / account_service / `account_8858` | Evidence/state | `dataset/system_activity.csv` (event timestamps and claim shown in diagnostic CSV) |

## Screenshot and PDF check

- Exact set intersection of the 29 missing resource IDs with all manually transcribed PNG identifiers: **0 matches**. Evidence_42 names user_17 but no account resource ID; the other screenshots show different records/resources.
- PDFs: evidence_18 (account history, 717 extracted chars; user_18, no expected missing resource ID), evidence_27 (legal retention register, 1,001 chars; users user_08/user_12/user_17/user_21/user_24/user_29, no expected missing resource ID), evidence_55 (security extract, 618 chars; audit_record_003/user_03), evidence_58 (delivery attachment, 836 chars; support_001). PDF structural scan found no embedded image objects; text extraction is present, so OCR would not help.
- Current environment: Pillow installed; Tesseract executable, pytesseract, pypdf, PyMuPDF (`fitz`), pdfplumber, pdf2image, OpenCV, EasyOCR, and Torch are absent. No packages were installed.
- PNG placeholder behavior is an honest coverage limitation in `diagnostics/parser_coverage.csv` (zero extracted text); it should not be described as semantic parsing. For this mismatch set, visual review establishes no applicable image content, so an OCR dependency is not justified.

## Decision

No production parser or identity change is justified by the source evidence. The largest category has explicit resource IDs but no subject key; correlating those records to a requester would require unsupported inference. The post-cutoff records must remain excluded. Activity-only entries remain claims. Adding OCR or loosening joins would not recover a valid missing step. The case_04 expected COMPLETE label remains unsupported: account_004 is absent from evidence_54 and analytics_901 has null identity fields in evidence_56.
