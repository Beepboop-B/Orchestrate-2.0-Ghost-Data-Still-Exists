# AI Judge Interview Preparation

Use this as a factual study guide, not a script. Describe only behavior present
in the current code and tests.

## 60-second architecture explanation

The submission is a deterministic Python deletion auditor. It resolves each
request email against current and historical identity data, parses evidence
with its source and timestamps, and links records using supported identifiers.
The engine reconstructs resource state at `audit_at`, applies the supplied
deletion policy, and creates ordered findings, remediation, and verification
steps. A tightly gated account activity correlation can nominate an account
resource, but separate evidence must prove its state. The output validator
checks the 518-row CSV, step schema, ordering, evidence references, and time
cutoffs. The current sample score is 31/32 statuses and 17/32 exact ordered
sequences; missing or ambiguous links remain the main limitation.

## Pipeline walkthrough

1. **Load inputs** (`code/data.py`, `code/main.py`): validate CSV schemas and
   load requests, identities, identity history, activity, deletion rules, and
   the evidence manifest. Paths are relative to the repository.
2. **Resolve identity** (`code/identity.py`): resolve the request email to one
   user using only identity snapshots and audit-log events available by the
   cutoff. Gather current and historical identifiers. Ambiguous matches fail
   closed.
3. **Parse and link evidence** (`code/evidence.py`, `code/audit.py`): preserve
   each file ID, system, resource, manifest `captured_at`, and record
   `observed_at`. Structured identifier fields and supported text matches
   associate evidence with a subject. Both time fields must be at or before
   `audit_at`.
4. **Reconstruct state** (`code/state.py`): use direct record observations,
   completed reads, and matching snapshot scopes. A lookup-start event is not
   a state result. The latest eligible evidence determines the reconstructed
   state; replica-specific collections are kept separate.
5. **Apply policy and plan** (`code/policy.py`, `code/engine.py`,
   `code/planner.py`): decide whether each linked record must be deleted,
   redacted, anonymized, retained, or protected from a flow/restore risk.
   Current findings cite evidence; proposed remediation and future checks use
   empty evidence IDs. Complete-state checks cite current evidence.
6. **Validate and evaluate** (`code/validation.py`,
   `code/evaluation/main.py`): validate the production CSV against request IDs,
   step rules, evidence IDs, and audit cutoffs. The sample evaluator compares
   status, step count, aligned fields, and exact ordered sequences with the
   supplied public answers.

## Identity, provenance, and point-in-time state

The current identity snapshot and `user_audit_log.csv` supply user IDs and
current/historical identifiers. For exact account ownership tie-breaking, the
code uses exact email and user-ID values plus historical phone/hash values from
the audit log; plain text must contain a boundary-delimited exact identifier.
Name-only, current phone/hash, trace proximity, and time proximity do not create
an exact ownership edge.

Evidence availability has two separate bounds: the outer manifest capture and
the record's observation time. Both must be at or before `audit_at`. An older
account identity link observed before `requested_at` cannot attach that
resource to a later request. A scope snapshot can prove a resource absent only
after a resource-to-subject link has been established.

## Account correlation and its heuristic limits

There are two candidate paths in `code/audit.py`:

- The status-consistent primary-profile path accepts `DELETE_RECORD` activity
  targeting `account_service`, with `COMPLETE → SUCCESS`,
  `NOT_STARTED → FAILED`, or `PARTIALLY_COMPLETE → PARTIAL/SUCCESS`. It uses
  0.70–1.30 hours before `reported_at`, or up to 15 minutes after it, with the
  event between `requested_at` and `audit_at`. Exact identity ownership can
  remove a cross-case candidate. Single activity claims propagate one-to-one
  across the full request universe; ambiguous candidates are left unassigned.
- A legacy fallback accepts one activity within 90 minutes of `reported_at`
  only when exactly one event matches the request and exactly one request
  window in the full request universe. It also applies `requested_at` and
  `audit_at` bounds. This 90-minute tolerance is a heuristic, not a threshold
  defined in the challenge contract.

Neither path proves state. The engine requires independently reconstructed
`ABSENT` account state and the evidence cutoff before emitting an absence
verification. Activity results remain claims, never proof of deletion.

## Tests and current evaluation

The latest run passed **69/69 unit tests**. The public evaluator reports:

- Status accuracy: **31/32 (96.88%)**
- Step-count accuracy: **18/32 (56.25%)**
- Aligned step-field accuracy: **1116/1211 (92.16%)**
- Exact ordered-sequence accuracy: **17/32 (53.12%)**

The evaluator's mismatch matrix shows one status mismatch, 20 missing
resources/phase steps, no extra resources/steps, no operation/state field
mismatches, one wrong evidence reference, and no ordering-only cases. Passing
unit tests confirms tested rule behavior, not benchmark completeness.

Team-authored cases include:

1. A request that is not a deletion request returns `NOT_APPLICABLE` with no
   steps.
2. An incomplete finding with an evidence ID outside the manifest is rejected.
3. An activity shared by multiple requests is not assigned unless unique
   one-to-one propagation resolves it.
4. A pre-request account identity link cannot support later state, even if a
   later broad scope snapshot exists.
5. A `COMPLETE` prediction cannot contain remediation instead of cited
   verification.

## Experiments and limitations

- The final account rule and exact-identity tie-break were retained after
  sample evaluation. Relative to the pre-account baseline, metrics rose from
  13/32 to 17/32 exact sequences and from 87.28% to 92.16% aligned fields.
  The final account candidate changes 157 full-set rows; three status changes
  are supported by evidence_66 absence scopes.
- The observed-at-only cutoff relaxation was rejected: it caused status
  regressions and no exact-sequence gain. Manifest capture remains an
  availability bound even when an embedded observation is older.
- A 20–40-minute analytics wave trial remained ambiguous or failed the status
  mapping. The activity stream has no `RETAIN_RECORD` or
  `VERIFY_RECORD_PRESENT` event for `security_service`; no analytics or
  audit-record correlation was added.
- The old account_6523 readback in evidence_67 predates case_17's request. It
  does not prove post-request state; the final candidate omits that step.
- Case_04 remains the status mismatch: the evidence does not link account_004
  or analytics_901 to its requester. Other missing resource links and one
  evidence-reference mismatch remain unresolved. Exact sequence accuracy is
  17/32, not a claim of full benchmark coverage.
- The generated output was validated and a fresh current-source generation
  reproduced it byte-for-byte. This verifies deterministic reproduction, not
  hidden-answer correctness.

## Likely judge questions

**Why not use the reported workflow result as proof?**
It is an operational claim. The engine requires an independent, cutoff-safe
record or snapshot to establish state.

**How is temporal leakage prevented?**
Both manifest capture and record observation must be at or before `audit_at`.
Identity-linked account evidence must also be observed at or after the request
time before it can support that later request.

**How are ambiguous activity events handled?**
Candidate events are filtered by system, operation, time, and status where
applicable, then propagated one-to-one across the full request population.
Unresolved candidates produce no account step.

**Why is the correlation threshold acceptable?**
It is a measured heuristic, not an official contract constant. The implementation
keeps a strict uniqueness check and independent state proof, and the README and
evaluation report disclose the heuristic and its limits.

**What remains uncertain?**
The 17/32 exact-sequence result shows unresolved links, evidence references,
and ordering. In particular, the public case_04 expectations lack an eligible
subject/resource link in the participant evidence.

**What did the predictor cost to run?**
No model or API is called by prediction. Model calls, prediction tokens, and
prediction API cost are zero; development token/cost telemetry is unavailable
and is not estimated.
