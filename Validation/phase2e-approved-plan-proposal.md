# Phase 2E.3 — Approved Edit Plan Proposal + Global Limits

## Scope

Phase 2E.3 introduces a **non-executable approved Edit Plan proposal** between individually valid promotion approvals and any future global execution authorization.

It does **not** authorize semantic rendering, auto-apply or an executable Edit Plan.

## Inputs

- `analysis.json` schema v9 or higher;
- one or more `promotion_approval.json` schema v1 records;
- every supplied approval must still validate as `valid_approved` against the exact current analysis.

## Artifact

```text
approved_edit_plan_proposal.json
schema_version = 1
record_type = approved_edit_plan_proposal
```

A positive proposal uses:

```text
status = proposal_ready_for_global_review
proposed_edits[]
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

`proposed_edits[]` is deliberately different from the executable Edit Plan key `edits[]`.

## Supported candidate class

```text
possible_repetition
```

No other semantic candidate kind is promoted in this phase.

## Precommitted global limits

The limits were fixed before observing validation results and are identical in conservative and aggressive modes:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

No threshold was changed to make the test suite pass.

## Fail-safe blockers

The whole proposal is blocked rather than partially salvaged if any supplied approval or target fails the contract.

Covered blockers:

```text
blocked_no_approved_records
blocked_invalid_or_conflicting_approval
blocked_overlapping_approved_targets
blocked_global_limits
```

Concrete veto causes include:

- stale analysis approval;
- stale evidence approval;
- rejected approval;
- invalid/tampered approval;
- duplicate approved candidate/promotion target;
- unsupported candidate kind;
- missing/invalid target;
- target outside source timeline;
- overlapping approved targets;
- more than 10 semantic edits;
- more than 30 seconds removed;
- more than 5% of source duration removed.

Any blocker returns:

```text
proposed_edits = []
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
```

## CLI

```text
video-tunner proposal build ANALYSIS \
  --approval approval1.json \
  --approval approval2.json \
  --output approved_edit_plan_proposal.json
```

Exit code is success only when the result is `proposal_ready_for_global_review`; blocked proposals are still written for auditability and return a non-zero status.

## Renderer isolation

The existing renderer is intentionally isolated from proposal artifacts in two independent ways:

1. proposals use `proposed_edits[]`, not executable `edits[]`;
2. `render_from_plan` explicitly raises `ValueError` if a plan contains `proposed_edits`.

Therefore a proposal cannot silently pass through the current renderer as an executable semantic Edit Plan.

## Validation run — proposal foundation

GitHub Actions run:

```text
33900544072
```

Result:

```text
185/185 tests PASS in 5.144 s
doctor PASS
```

Relevant 2E.3 tests passed:

- `test_limits_are_precommitted_and_mode_independent`;
- `test_valid_approved_records_create_review_only_proposal`;
- `test_rejected_approval_vetoes_entire_proposal`;
- `test_stale_approval_vetoes_entire_proposal`;
- `test_duplicate_approval_vetoes_entire_proposal`;
- `test_overlapping_targets_veto_entire_proposal`;
- `test_target_outside_source_timeline_vetoes_entire_proposal`;
- `test_max_edit_count_is_enforced_independently`;
- `test_max_removed_seconds_is_enforced_independently`;
- `test_max_removed_fraction_is_enforced_independently`;
- `test_no_approvals_is_blocked`.

## Final validation — renderer hardening

GitHub Actions run:

```text
33908500929
```

Result:

```text
186/186 tests PASS in 7.887 s
doctor PASS
```

Additional final gate:

```text
test_renderer_rejects_non_executable_plan_proposal ... ok
```

The run also reconfirmed all approval, eligibility, join, acoustic, semantic, sync and FFmpeg regression tests.

## CI hygiene

- core CI used deliberately;
- workflow restored to `workflow_dispatch` only;
- no model/video/ZIP artifacts uploaded;
- no public Release created.

## Closure decision

**Phase 2E.3: COMPLETE.**

The repository now has a bounded, auditable proposal layer from valid individual approvals, while semantic execution remains impossible through this path without a future global authorization contract.

## Next

Phase 2E.4 — **Execution Authorization / Semantic Render Gate**:

- separate global authorization artifact;
- exact analysis + proposal fingerprint binding;
- actor/reason/timestamp audit fields;
- stale/tampered authorization fail-safe;
- explicit materialization proposal → executable Edit Plan;
- preserve full provenance;
- semantic render gate and later post-render verification.
