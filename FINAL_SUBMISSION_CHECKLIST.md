# Final Submission Checklist

Repository: `D:\HackathonWorkspace\hackerrank-orchestrate-october26`

## Upload files

| Filename | Exact path | SHA-256 | Validation | Upload slot / status |
|---|---|---|---|---|
| `output.csv` | `output.csv` | `edb1fc5696265f435fd93850e505758197be536fb88a9a507896cdb6da838c15` | PASS: 518 rows, sorted, unique, official validator passed; current-source reproduction and saved backup match byte-for-byte | Required `output.csv` upload |
| `code.zip` | `code.zip` | `6f10abdc34f153c230f81d06b6b034ca63791fe54e4cdaecc05336d23d5c7c4c` | PASS: 28 entries; all code modules/tests and required docs present; no dataset, cache, virtual environment, secret file, or nested archive | Required `code.zip` upload |
| `log.txt` | `log.txt` | `27f40698232bff63657a01f06822afbda6430cb970296980af80ce39d2c0c4c9` | Current entries use the required format. Earlier malformed/misordered headings and a misplaced duplicate are preserved and documented in append-only correction notes. | Required `chat_transcript` upload |

The AI interview is a live interview, not a file upload. `code/evaluation/`
contains the required `evaluation_report.md`, `usage_report.md`, and the
supporting `interview_prep.md`.

## Separate trace artifact

| Filename | Exact path | SHA-256 | Validation | Upload slot / status |
|---|---|---|---|---|
| `agent-trace.zip` | `agent-trace.zip` | `759e6929e21564750c8fb4638a62839d3818af2ec131db64136f2fcb081dd010` | Contains three Aider histories, one Codex rollout ending 2026-10-24, and `TRACE_STATUS.md`; no auth/config/env files or plaintext credential patterns. Six token-shaped strings remain only inside encrypted Codex payloads. | Separate trace artifact requested by `agent_trace_instructions.md`; **PROVISIONAL** |

The active hosted Codex session for this final folder audit is not in the
archive. The current session has no available local rollout in this
environment. After it closes, add a matching Orchestrate-only rollout if an
export is available, scan/redact it, rebuild the trace ZIP, and update its
hash. If no export is available, retain the provisional status and note that
the hosted session has no local trace. Do not submit the current archive as a
complete trace of every challenge session.

## Validation summary

- Unit tests: 69 passed.
- Public sample metrics: status 31/32, step count 18/32, aligned fields
  1116/1211, exact ordered sequences 17/32.
- Full output: 518 rows; validator passed; current-source reproduction is
  byte-for-byte identical to root `output.csv`.
- Full-set change from the pre-promotion baseline: 157 rows, each adding one
  uniquely assigned account absence verification; three cases also change
  status to COMPLETE based on evidence_66.
- Remaining score limitations: one status mismatch (case_04), 20 missing
  resources/steps, one evidence-reference mismatch, and no proven
  hidden-answer accuracy beyond the public sample.
- `code.zip` is the only bundle containing `README.md` and `code/`; neither
  `dataset/` nor the trace archive is nested inside it.
- `agent-trace.zip` remains provisional for complete session coverage.

The root `FINAL_SUBMISSION_CHECKLIST.md`, `code/evaluation/interview_prep.md`,
and `.accuracy-baseline/final_submission_output_backup.csv` are supporting
artifacts, not additional official output/code upload slots.
