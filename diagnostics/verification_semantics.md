# Future Verification Planning Audit

## Contract rule

`problem_statement.md` permits only `VERIFY_RECORD_ABSENT/ABSENT`,
`VERIFY_RECORD_PRESENT/PRESENT`, `VERIFY_RECORD_REDACTED/REDACTED`,
`VERIFY_RECORD_ANONYMIZED/ANONYMIZED`, `VERIFY_DATA_FLOW_DISABLED/DISABLED`,
and `VERIFY_RESTORE_BLOCKED/BLOCKED` in `VERIFICATION`. For `COMPLETE`, checks
must cite evidence that proves state at `audit_at`. For `INCOMPLETE`, future
checks have empty `evidence_id` and must pass after the remediation plan. The
contract also requires subject/resource relevance and excludes post-cutoff
evidence; workflow and activity results are claims.

It does not say that every request should receive a verification for every
resource in a system. The resource must first be grounded as relevant to that
request. For an incomplete plan, the engine currently creates verification
steps alongside a policy violation on a linked resource; `build_steps` only
orders and serializes the supplied verification items. This is a consequence of
candidate/state construction, not a separate planner filter.

## Sample comparison

The 13 exact sample cases are `case_01`, `case_02`, `case_05` through
`case_08`, `case_11` through `case_16`, and `case_19`. The other 19 are
non-exact. They contain 29 missing verification phase-steps and one extra
phase-step; `case_17` has the extra step but no missing verification. The
missing-step rows are all in the non-exact group.

The production path in `code/engine.py` forms resource candidates from
identity-linked evidence, then asks `reconstruct_resource_state` for eligible
state. If no state is established, the engine skips the resource. If the
linked state violates policy, it emits findings/remediation and a corresponding
future verification; if compliant, it emits an evidence-backed verification.
For exact authorized samples that contain steps, the relevant identities,
resource records, and states were linkable at their cutoffs. Exact
`NOT_APPLICABLE` samples correctly have no steps. The misses below are lost
before `build_steps` can order them.

## Missing verification groups

| Expected operation | Count | Missing case/resource | Participant-facing evidence assessment |
|---|---:|---|---|
| `VERIFY_RECORD_ABSENT` (`account_service`) | 15 | `case_04/account_004`; `case_09/account_3960`; `case_10/account_010`; `case_18/account_5521`; `case_20/account_5037`; `case_21/account_6440`; `case_22/account_4990`; `case_23/account_410`; `case_25/account_3136`; `case_26/account_5684`; `case_27/account_3866`; `case_28/account_5482`; `case_29/account_7012`; `case_31/account_4857`; `case_32/account_8858` | `case_04`: evidence_54 is a scoped SQL snapshot with no `account_004` row. `case_09`: evidence_06 was captured after the audit cutoff. `case_10`, `18`, `20`, `22`, `23`, `29`, and `32`: only activity rows name the account resource; their manifest schema has no requester/user field, and results are claims. `case_21`, `25`, and `28`: evidence_92 has the resource lookup but no matching requester identifier. `case_26` and `27`: evidence_92 lacks the link; evidence_02 contains it but its manifest capture is after audit_at. `case_31`: evidence_51 has no account resource or subject link; activity_3682 is only a claim. |
| `VERIFY_RECORD_ANONYMIZED` (`analytics_platform`) | 7 | `case_03/analytics_9406`; `case_04/analytics_901`; `case_21/analytics_5335`; `case_25/analytics_1895`; `case_26/analytics_4566`; `case_27/analytics_4574`; `case_28/analytics_6077` | The resource rows are present in eligible evidence_94 (case_03), evidence_56 (case_04), or evidence_92 (the remaining cases), but their requester identity fields are null and no explicit eligible correlation is present. Nearby ANONYMIZE activity results are claims. Some evidence_02 snapshots contain links, but their manifest capture is 2026-09-17, after the relevant 2026-09-15 audits. |
| `VERIFY_RECORD_PRESENT` (`security_service`) | 7 | `case_09/audit_record_4902`; `case_18/audit_record_6645`; `case_20/audit_record_5569`; `case_23/audit_record_4128`; `case_24/audit_record_7095`; `case_29/audit_record_3954`; `case_30/audit_record_1707` | `case_18` and `case_20` have no participant-facing record or explicit resource-to-subject link. `case_09`'s matching log capture is after cutoff. The remaining four have subject-linked rows in evidence_02, but that bundle's manifest capture is after audit_at. |

These are all 29 rows in `diagnostics/per_case_misses.csv` with the three
verification operations. The row-level timestamps, first divergence, and
evidence descriptions remain available in that CSV and
`diagnostics/pipeline_diagnostic.csv`.

## Candidate-rule assessment

No policy-driven planner rule is supported across these groups:

- A system/category policy (for example, retain security audits or anonymize
  analytics) chooses treatment; it does not establish that a specific global
  resource belongs to the requester.
- An identity row or system-wide scope does not prove that a particular
  account, analytics, or security resource exists for that person.
- The activity-only account candidates lack an explicit user/resource join.
  Treating `SUCCESS`, `FAILED`, or proximity to `reported_at` as ownership or
  resulting state would exceed the evidence contract.
- The four security snapshot records and other evidence_02 links are not
  available at the relevant audit cutoffs because the manifest capture is
  later. Their nested timestamps do not change that.
- A future verification may have an empty evidence reference, but that does
  not remove the need to identify the target resource as relevant or connect it
  to an authorized remediation/retention requirement. No predicted remediation
  exists for these missing resource targets, and the expected answers supply
  verification-only targets for several of them.

The benchmark therefore asks for some verification-only resources that cannot
be tied to the requester using eligible evidence under the stated identity,
provenance, and cutoff rules. In particular, it is ambiguous whether an
activity-only target or a policy-category expectation is intended to suffice
for a *future* check when there is no eligible resource-to-requester link. The
contract's evidence rules do not authorize such an inference. No production
change or regression test was added because any rule that fills these steps
would need to relax that grounding requirement or accept post-cutoff evidence.
In a separate bounded safety experiment, the later source removed an unrelated
account fallback based on proximity to `reported_at`; it did not fill these
missing verification targets.

## Verification run

The diagnostic `evaluate()` path returned status `31/32`, step-count `13/32`,
aligned-field `1002/1148 (87.28%)`, and exact-sequence `13/32`. The protected
root `output.csv` SHA-256 was checked before this review and remained
`5692c6b00320d69bb17e589a3a77a093b3b88e8cd3a3d0be2ccb6488d86bcc2c`; no
prediction or packaging files were changed.
