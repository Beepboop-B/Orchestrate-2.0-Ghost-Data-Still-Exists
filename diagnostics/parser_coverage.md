# Parser Coverage Report

- Manifest files: 94
- Parse successes: 94
- Parse failures: 0
- Unsupported file extensions: 0
- Manifest types: .json 28, .log 26, .pdf 4, .png 11, .sql 24, .txt 1

## Parser/environment findings

- `.json` files use `_parse_json`; `.sql` files execute in an in-memory SQLite database via `_parse_sql`; `.log`/`.txt` use `_parse_text_records` (timestamped JSON, shlex key/value, handover rows, plus whole-text retention); `.pdf` uses the project's custom `_pdf_text` stream/literal-string reader.
- `.png` files currently hit the generic image placeholder: zero records with zero extracted text. Pillow is installed and image dimensions are readable, but `pytesseract`, Tesseract executable, PyMuPDF, pypdf, pdf2image, OpenCV, EasyOCR, and Torch are absent. No packages were installed.
- All 11 PNGs were actually viewed with the image viewer in this run; they contain readable screenshot text. The production pipeline does not extract that text, so the report separates manually observed IDs from machine-extracted IDs. OCR is a real capability gap.
- PDFs were parsed with the custom reader and structurally checked for page/image objects. `fpdf2` is installed but is a PDF generator, not a parser. No PDF parser or OCR dependency was installed.
- No manifest extension is unsupported; the gap is semantic extraction from images and the limits of the custom PDF parser, not manifest discovery.

## Per-parser totals

| Extension | Parser | Files | Parsed files | Records | Parser text chars |
|---|---|---:|---:|---:|---:|
| .json | `_parse_json` | 28 | 28 | 890 | 0 |
| .log | `_parse_text_records (JSON/shlex/handover)` | 26 | 26 | 1297 | 513989 |
| .pdf | `_pdf_text (custom stream text extraction)` | 4 | 4 | 4 | 3172 |
| .png | `image placeholder (no OCR)` | 11 | 11 | 11 | 0 |
| .sql | `_parse_sql (sqlite3)` | 24 | 24 | 1199 | 0 |
| .txt | `_parse_text_records (JSON/shlex/handover)` | 1 | 1 | 42 | 4488 |

## Per-file inventory

The CSV provides one row for each manifest file, with machine-extracted resource IDs, stable user IDs, direct/historical identity fields, lookup/correlation keys, timestamps, parser errors, and screenshot/PDF review flags. Manually observed screenshot IDs/notes are in separate columns and were not fed to production predictions. `extracted_text_characters` counts the longest full-text artifact retained for text/PDF parsers; JSON/SQL use structured records rather than flattened text.

- `evidence_01` `evidence/logs/service_events_ap_south_20260915.log`: _parse_text_records (JSON/shlex/handover); parsed; records=64; text_chars=22133; resources=36; stable_users=10; lookup_keys=26
- `evidence_02` `evidence/records/customer_data_snapshot_bundle_20260917.json`: _parse_json; parsed; records=41; text_chars=0; resources=41; stable_users=10; lookup_keys=0
- `evidence_03` `evidence/records/customer_account_handover_20261001.txt`: _parse_text_records (JSON/shlex/handover); parsed; records=42; text_chars=4488; resources=41; stable_users=10; lookup_keys=0
- `evidence_04` `evidence/images/account_admin_console_20260926.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1200; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=user_11; account_5762; support_9538; Customer profile screenshot; direct email and phone visible.
- `evidence_05` `evidence/databases/customer_data_read_replica_20260921.sql`: _parse_sql (sqlite3); parsed; records=67; text_chars=0; resources=31; stable_users=10; lookup_keys=0
- `evidence_06` `evidence/logs/structured_service_events_eu_west_20260918.log`: _parse_text_records (JSON/shlex/handover); parsed; records=70; text_chars=31199; resources=36; stable_users=10; lookup_keys=24
- `evidence_07` `evidence/records/customer_data_snapshot_bundle_20260913.json`: _parse_json; parsed; records=30; text_chars=0; resources=30; stable_users=10; lookup_keys=0
- `evidence_08` `evidence/logs/search_index_diagnostic_20260906.log`: _parse_text_records (JSON/shlex/handover); parsed; records=37; text_chars=8013; resources=35; stable_users=10; lookup_keys=0
- `evidence_09` `evidence/images/search_index_inspector_20260901.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1100; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=user_13; search_428; search_1874; user_9842; Search screenshot; two hits and a customer-reference timeline are visible; contact identifiers visible.
- `evidence_10` `evidence/databases/customer_data_read_replica_20260827.sql`: _parse_sql (sqlite3); parsed; records=65; text_chars=0; resources=30; stable_users=10; lookup_keys=0
- `evidence_11` `evidence/logs/syslog_archive_us_east_20260824.log`: _parse_text_records (JSON/shlex/handover); parsed; records=37; text_chars=26414; resources=36; stable_users=10; lookup_keys=4
- `evidence_12` `evidence/records/customer_data_snapshot_bundle_20260819.json`: _parse_json; parsed; records=29; text_chars=0; resources=29; stable_users=10; lookup_keys=0
- `evidence_13` `evidence/records/connector_configurations_20260812.json`: _parse_json; parsed; records=39; text_chars=0; resources=38; stable_users=10; lookup_keys=0
- `evidence_14` `evidence/images/connector_management_console_20260807.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1150; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=data_flow_1121; data_flow_9846; Connector topology screenshot; email selectors are visible.
- `evidence_15` `evidence/databases/customer_data_read_replica_20260802.sql`: _parse_sql (sqlite3); parsed; records=56; text_chars=0; resources=25; stable_users=10; lookup_keys=0
- `evidence_16` `evidence/logs/application_trace_ap_northeast_20260730.log`: _parse_text_records (JSON/shlex/handover); parsed; records=37; text_chars=18839; resources=35; stable_users=10; lookup_keys=9
- `evidence_17` `evidence/records/customer_data_snapshot_bundle_20260725.json`: _parse_json; parsed; records=36; text_chars=0; resources=36; stable_users=10; lookup_keys=0
- `evidence_18` `evidence/documents/account_history_report_20260718.pdf`: _pdf_text (custom stream text extraction); parsed; records=1; text_chars=717; resources=0; stable_users=1; lookup_keys=0; pages=2; image_objects=0; OCR_needed_possible=False
- `evidence_19` `evidence/images/analytics_profile_view_20260713.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1150; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=user_20; analytics_7438; Analytics profile screenshot; direct email visible.
- `evidence_20` `evidence/databases/customer_data_read_replica_20260708.sql`: _parse_sql (sqlite3); parsed; records=70; text_chars=0; resources=32; stable_users=10; lookup_keys=0
- `evidence_21` `evidence/logs/operations_stream_eu_central_20260705.log`: _parse_text_records (JSON/shlex/handover); parsed; records=129; text_chars=26198; resources=39; stable_users=10; lookup_keys=0
- `evidence_22` `evidence/records/customer_data_snapshot_bundle_20260630.json`: _parse_json; parsed; records=71; text_chars=0; resources=69; stable_users=10; lookup_keys=0
- `evidence_23` `evidence/images/customer_export_console_20260618.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1100; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=export_1261; export_1260; export_1259; export_1258; Export jobs screenshot; owner email values visible.
- `evidence_24` `evidence/databases/customer_data_read_replica_20260613.sql`: _parse_sql (sqlite3); parsed; records=57; text_chars=0; resources=25; stable_users=10; lookup_keys=0
- `evidence_25` `evidence/logs/cloud_runtime_export_us_west_20260608.log`: _parse_text_records (JSON/shlex/handover); parsed; records=1; text_chars=32266; resources=43; stable_users=10; lookup_keys=0
- `evidence_26` `evidence/records/customer_data_snapshot_bundle_20260605.json`: _parse_json; parsed; records=32; text_chars=0; resources=32; stable_users=10; lookup_keys=0
- `evidence_27` `evidence/documents/legal_retention_register_20260529.pdf`: _pdf_text (custom stream text extraction); parsed; records=1; text_chars=1001; resources=0; stable_users=6; lookup_keys=0; pages=2; image_objects=0; OCR_needed_possible=False
- `evidence_28` `evidence/images/support_ticket_console_20260524.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1200; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=support_1034; CS-5034; Support-ticket screenshot; direct name and email visible.
- `evidence_29` `evidence/databases/customer_data_regional_replicas_20260519.sql`: _parse_sql (sqlite3); parsed; records=110; text_chars=0; resources=29; stable_users=10; lookup_keys=0
- `evidence_30` `evidence/logs/service_events_sa_east_20260516.log`: _parse_text_records (JSON/shlex/handover); parsed; records=69; text_chars=23481; resources=37; stable_users=10; lookup_keys=26
- `evidence_31` `evidence/records/customer_data_snapshot_bundle_20260511.json`: _parse_json; parsed; records=74; text_chars=0; resources=73; stable_users=10; lookup_keys=0
- `evidence_32` `evidence/images/backup_restore_console_20260429.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1150; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=backup_9291; backup_9288; backup_9287; backup_9286; Backup archive console screenshot; account email values visible.
- `evidence_33` `evidence/databases/customer_data_regional_replicas_20260424.sql`: _parse_sql (sqlite3); parsed; records=111; text_chars=0; resources=31; stable_users=10; lookup_keys=0
- `evidence_34` `evidence/logs/structured_service_events_ca_central_20260419.log`: _parse_text_records (JSON/shlex/handover); parsed; records=78; text_chars=38660; resources=44; stable_users=10; lookup_keys=26
- `evidence_35` `evidence/records/customer_data_snapshot_bundle_20260416.json`: _parse_json; parsed; records=28; text_chars=0; resources=28; stable_users=10; lookup_keys=0
- `evidence_36` `evidence/records/customer_export_manifest_20260409.json`: _parse_json; parsed; records=46; text_chars=0; resources=43; stable_users=10; lookup_keys=0
- `evidence_37` `evidence/images/security_audit_explorer_20260905.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1100; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=user_03; audit_record_003; audit_record_002; audit_record_001; audit_record_006; audit_record_005; audit_record_004; Security event screenshot; six event references visible.
- `evidence_38` `evidence/databases/customer_data_regional_replicas_20260330.sql`: _parse_sql (sqlite3); parsed; records=104; text_chars=0; resources=29; stable_users=10; lookup_keys=0
- `evidence_39` `evidence/logs/syslog_archive_ap_southeast_20260325.log`: _parse_text_records (JSON/shlex/handover); parsed; records=41; text_chars=25968; resources=40; stable_users=10; lookup_keys=8
- `evidence_40` `evidence/records/customer_data_snapshot_bundle_20260322.json`: _parse_json; parsed; records=31; text_chars=0; resources=30; stable_users=10; lookup_keys=0
- `evidence_41` `evidence/logs/notification_delivery_20260315.log`: _parse_text_records (JSON/shlex/handover); parsed; records=40; text_chars=8972; resources=39; stable_users=10; lookup_keys=0
- `evidence_42` `evidence/images/deleted_account_reference_20260310.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1100; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=user_17; ORD-20263245; CS-3245; CS-3378; FIN-7742; Retained customer-reference screenshot; no account resource ID is shown.
- `evidence_43` `evidence/databases/customer_data_reporting_replica_20260305.sql`: _parse_sql (sqlite3); parsed; records=68; text_chars=0; resources=25; stable_users=10; lookup_keys=0
- `evidence_44` `evidence/logs/application_trace_eu_north_20260302.log`: _parse_text_records (JSON/shlex/handover); parsed; records=42; text_chars=24885; resources=39; stable_users=10; lookup_keys=6
- `evidence_45` `evidence/records/customer_data_snapshot_bundle_20260223.json`: _parse_json; parsed; records=75; text_chars=0; resources=73; stable_users=10; lookup_keys=0
- `evidence_46` `evidence/images/object_storage_browser_20260213.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1800x1150; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed: Object listing screenshot; filenames visible, but no customer user/resource ID shown.
- `evidence_47` `evidence/databases/customer_data_reporting_replica_20260208.sql`: _parse_sql (sqlite3); parsed; records=68; text_chars=0; resources=23; stable_users=10; lookup_keys=0
- `evidence_48` `evidence/logs/operations_stream_me_central_20260203.log`: _parse_text_records (JSON/shlex/handover); parsed; records=104; text_chars=21199; resources=36; stable_users=10; lookup_keys=0
- `evidence_49` `evidence/records/customer_data_snapshot_bundle_20260131.json`: _parse_json; parsed; records=34; text_chars=0; resources=34; stable_users=10; lookup_keys=0
- `evidence_50` `evidence/records/security_audit_ledger_20261001.json`: _parse_json; parsed; records=20; text_chars=0; resources=20; stable_users=10; lookup_keys=0
- `evidence_51` `evidence/records/customer_data_snapshot_bundle_20260915.json`: _parse_json; parsed; records=4; text_chars=0; resources=4; stable_users=2; lookup_keys=0
- `evidence_52` `evidence/databases/customer_data_failover_replica_20260920.sql`: _parse_sql (sqlite3); parsed; records=36; text_chars=0; resources=16; stable_users=8; lookup_keys=0
- `evidence_53` `evidence/logs/cloud_runtime_export_af_south_20260930.log`: _parse_text_records (JSON/shlex/handover); parsed; records=1; text_chars=94518; resources=300; stable_users=0; lookup_keys=0
- `evidence_54` `evidence/databases/customer_accounts_failover_replica_20260902.sql`: _parse_sql (sqlite3); parsed; records=9; text_chars=0; resources=4; stable_users=4; lookup_keys=0
- `evidence_55` `evidence/documents/security_retention_extract.pdf`: _pdf_text (custom stream text extraction); parsed; records=1; text_chars=618; resources=1; stable_users=1; lookup_keys=0; pages=1; image_objects=0; OCR_needed_possible=False
- `evidence_56` `evidence/records/customer_analytics_report_20260907.json`: _parse_json; parsed; records=2; text_chars=0; resources=2; stable_users=1; lookup_keys=0
- `evidence_57` `evidence/databases/customer_search_primary_20260910.sql`: _parse_sql (sqlite3); parsed; records=4; text_chars=0; resources=3; stable_users=0; lookup_keys=0
- `evidence_58` `evidence/documents/delivery_correction_attachment.pdf`: _pdf_text (custom stream text extraction); parsed; records=1; text_chars=836; resources=1; stable_users=0; lookup_keys=0; pages=2; image_objects=0; OCR_needed_possible=False
- `evidence_59` `evidence/records/customer_export_jobs_20260914.json`: _parse_json; parsed; records=2; text_chars=0; resources=2; stable_users=0; lookup_keys=0
- `evidence_60` `evidence/images/marketing_profile_console.png`: image placeholder (no OCR); parsed; records=1; text_chars=0; resources=0; stable_users=0; lookup_keys=0; PNG 1500x920; visually inspected; text present; production parser extracts none (OCR unavailable); manually observed (not parser output): IDs=marketing_001; Marketing profile screenshot; direct email and phone visible.
- `evidence_61` `evidence/logs/support_replica.log`: _parse_text_records (JSON/shlex/handover); parsed; records=8; text_chars=1863; resources=4; stable_users=0; lookup_keys=3
- `evidence_62` `evidence/records/service_resource_export_20260129_114459.json`: _parse_json; parsed; records=29; text_chars=0; resources=29; stable_users=3; lookup_keys=5
- `evidence_63` `evidence/databases/customer_data_inventory_20260213.sql`: _parse_sql (sqlite3); parsed; records=32; text_chars=0; resources=17; stable_users=4; lookup_keys=0
- `evidence_64` `evidence/logs/resource_lookup_trace_20260218_083911.log`: _parse_text_records (JSON/shlex/handover); parsed; records=53; text_chars=10995; resources=26; stable_users=2; lookup_keys=12
- `evidence_65` `evidence/records/service_resource_export_20260228_103637.json`: _parse_json; parsed; records=27; text_chars=0; resources=27; stable_users=4; lookup_keys=5
- `evidence_66` `evidence/databases/customer_data_inventory_20260310.sql`: _parse_sql (sqlite3); parsed; records=39; text_chars=0; resources=23; stable_users=2; lookup_keys=0
- `evidence_67` `evidence/logs/resource_lookup_trace_20260310_061801.log`: _parse_text_records (JSON/shlex/handover); parsed; records=3; text_chars=544; resources=1; stable_users=0; lookup_keys=1
- `evidence_68` `evidence/records/service_resource_export_20260320_072349.json`: _parse_json; parsed; records=25; text_chars=0; resources=25; stable_users=4; lookup_keys=6
- `evidence_69` `evidence/databases/customer_data_inventory_20260404.sql`: _parse_sql (sqlite3); parsed; records=34; text_chars=0; resources=18; stable_users=3; lookup_keys=0
- `evidence_70` `evidence/logs/resource_lookup_trace_20260414_054007.log`: _parse_text_records (JSON/shlex/handover); parsed; records=49; text_chars=9836; resources=24; stable_users=4; lookup_keys=14
- `evidence_71` `evidence/records/service_resource_export_20260429_083222.json`: _parse_json; parsed; records=28; text_chars=0; resources=28; stable_users=4; lookup_keys=5
- `evidence_72` `evidence/databases/customer_data_inventory_20260504.sql`: _parse_sql (sqlite3); parsed; records=36; text_chars=0; resources=21; stable_users=3; lookup_keys=0
- `evidence_73` `evidence/logs/resource_lookup_trace_20260509_104353.log`: _parse_text_records (JSON/shlex/handover); parsed; records=67; text_chars=13602; resources=33; stable_users=5; lookup_keys=15
- `evidence_74` `evidence/records/service_resource_export_20260514_114454.json`: _parse_json; parsed; records=25; text_chars=0; resources=25; stable_users=4; lookup_keys=5
- `evidence_75` `evidence/databases/customer_data_inventory_20260524.sql`: _parse_sql (sqlite3); parsed; records=40; text_chars=0; resources=24; stable_users=4; lookup_keys=0
- `evidence_76` `evidence/logs/resource_lookup_trace_20260529_074313.log`: _parse_text_records (JSON/shlex/handover); parsed; records=47; text_chars=9626; resources=23; stable_users=3; lookup_keys=13
- `evidence_77` `evidence/records/service_resource_export_20260603_083457.json`: _parse_json; parsed; records=27; text_chars=0; resources=27; stable_users=3; lookup_keys=4
- `evidence_78` `evidence/databases/customer_data_inventory_20260618.sql`: _parse_sql (sqlite3); parsed; records=34; text_chars=0; resources=19; stable_users=2; lookup_keys=0
- `evidence_79` `evidence/logs/resource_lookup_trace_20260623_053726.log`: _parse_text_records (JSON/shlex/handover); parsed; records=59; text_chars=12014; resources=29; stable_users=4; lookup_keys=14
- `evidence_80` `evidence/records/service_resource_export_20260628_062556.json`: _parse_json; parsed; records=24; text_chars=0; resources=24; stable_users=3; lookup_keys=5
- `evidence_81` `evidence/databases/customer_data_inventory_20260703.sql`: _parse_sql (sqlite3); parsed; records=40; text_chars=0; resources=24; stable_users=5; lookup_keys=0
- `evidence_82` `evidence/logs/resource_lookup_trace_20260713_093359.log`: _parse_text_records (JSON/shlex/handover); parsed; records=53; text_chars=10662; resources=26; stable_users=4; lookup_keys=14
- `evidence_83` `evidence/records/service_resource_export_20260718_104335.json`: _parse_json; parsed; records=29; text_chars=0; resources=29; stable_users=3; lookup_keys=7
- `evidence_84` `evidence/databases/customer_data_inventory_20260723.sql`: _parse_sql (sqlite3); parsed; records=42; text_chars=0; resources=26; stable_users=2; lookup_keys=0
- `evidence_85` `evidence/logs/resource_lookup_trace_20260728_054417.log`: _parse_text_records (JSON/shlex/handover); parsed; records=45; text_chars=9052; resources=22; stable_users=3; lookup_keys=13
- `evidence_86` `evidence/records/service_resource_export_20260807_074104.json`: _parse_json; parsed; records=23; text_chars=0; resources=23; stable_users=3; lookup_keys=5
- `evidence_87` `evidence/databases/customer_data_inventory_20260817.sql`: _parse_sql (sqlite3); parsed; records=35; text_chars=0; resources=19; stable_users=2; lookup_keys=0
- `evidence_88` `evidence/logs/resource_lookup_trace_20260822_103910.log`: _parse_text_records (JSON/shlex/handover); parsed; records=45; text_chars=9059; resources=22; stable_users=3; lookup_keys=13
- `evidence_89` `evidence/records/service_resource_export_20260901_053316.json`: _parse_json; parsed; records=23; text_chars=0; resources=23; stable_users=1; lookup_keys=7
- `evidence_90` `evidence/databases/customer_data_inventory_20260905.sql`: _parse_sql (sqlite3); parsed; records=9; text_chars=0; resources=0; stable_users=0; lookup_keys=0
- `evidence_91` `evidence/logs/resource_lookup_trace_20260911_074253.log`: _parse_text_records (JSON/shlex/handover); parsed; records=61; text_chars=12248; resources=30; stable_users=6; lookup_keys=16
- `evidence_92` `evidence/records/service_resource_export_20260915_114455.json`: _parse_json; parsed; records=36; text_chars=0; resources=36; stable_users=5; lookup_keys=4
- `evidence_93` `evidence/databases/customer_data_inventory_20260916.sql`: _parse_sql (sqlite3); parsed; records=33; text_chars=0; resources=17; stable_users=3; lookup_keys=0
- `evidence_94` `evidence/logs/resource_lookup_trace_20260926_103856.log`: _parse_text_records (JSON/shlex/handover); parsed; records=57; text_chars=11743; resources=28; stable_users=3; lookup_keys=12

See `parser_coverage.csv` for the full extracted values and timestamps.
