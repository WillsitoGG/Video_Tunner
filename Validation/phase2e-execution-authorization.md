# Phase 2E.4 — Execution Authorization / Semantic Render Gate

## Scope

Phase 2E.4 introduces the first explicitly authorized semantic render path. It keeps four distinct artifacts/stages:

```text
promotion approval
→ bounded approved_edit_plan_proposal
→ semantic_execution_authorization
→ semantic_edit_plan
→ semantic render gate
→ FFmpeg render
```

No stage may bypass the previous one. `auto_apply` remains false.

## Global authorization artifact

```text
semantic_execution_authorization.json
schema_version = 1
record_type = semantic_execution_authorization
```

An authorization binds an explicit global APPROVE/REJECT decision to:

- exact `analysis.json` SHA-256;
- exact proposal SHA-256;
- canonical proposal execution snapshot/fingerprint;
- source provenance;
- mode and precommitted limits;
- exact `proposed_edits[]`;
- actor, reason and timestamp.

Valid statuses include:

```text
valid_authorized
valid_rejected
stale_analysis
stale_proposal
stale_evidence
stale_or_invalid_proposal
invalid_record
```

An APPROVE record may authorize materialization and the gated semantic render path, but the authorization record itself remains non-executable and never authorizes rendering the proposal directly:

```text
authorized = true
edit_plan_materialization_authorized = true
semantic_render_authorization = true
proposal_render_authorization = false
executable = false
auto_apply = false
```

## Semantic Edit Plan

```text
semantic_edit_plan.json
schema_version = 1
record_type = semantic_edit_plan
```

It can only be materialized while the exact current authorization revalidates as `valid_authorized`.

The plan stores:

- source file/duration/SHA-256;
- mode and inherited global limits;
- exact analysis/proposal/authorization SHA-256 provenance;
- proposal evidence fingerprint;
- `edits[]` derived exactly from approved `proposed_edits[]`;
- plan fingerprint;
- summary.

A valid materialized plan is explicit-render capable but not automatic:

```text
globally_authorized = true
requires_semantic_render_gate = true
executable = true
auto_apply = false
```

Any edit/fingerprint/provenance mutation invalidates the plan.

## Renderer isolation

Two independent boundaries exist:

1. `render_from_plan` always rejects `approved_edit_plan_proposal` artifacts containing `proposed_edits`;
2. generic `render_from_plan` also rejects `semantic_edit_plan` unless called through the internal semantic gate authorization path.

The public CLI semantic route is `execution render`, not the legacy `render` command.

## Semantic render gate

Immediately before FFmpeg, the gate revalidates:

1. analysis SHA-256;
2. proposal SHA-256 and proposal evidence;
3. global execution authorization;
4. authorization SHA-256 bound into the Semantic Edit Plan;
5. Semantic Edit Plan fingerprint and exact edits;
6. actual input source SHA-256 against analysis + proposal + plan.

Only then does it call the renderer with the semantic gate flag.

## CLI

```text
video-tunner execution authorize ANALYSIS PROPOSAL --decision approve|reject --actor ACTOR --reason REASON --output semantic_execution_authorization.json
video-tunner execution validate ANALYSIS PROPOSAL AUTHORIZATION
video-tunner execution materialize ANALYSIS PROPOSAL AUTHORIZATION --output semantic_edit_plan.json
video-tunner execution plan-validate ANALYSIS PROPOSAL AUTHORIZATION PLAN
video-tunner execution render-check INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN
video-tunner execution render INPUT ANALYSIS PROPOSAL AUTHORIZATION PLAN OUTPUT
```

The generic command remains intentionally separate:

```text
video-tunner render INPUT PLAN OUTPUT
```

and rejects Semantic Edit Plans.

## Core validation

GitHub Actions run:

```text
33909424933
```

Result:

```text
201/201 tests PASS in 7.310 s
doctor PASS
```

New contract coverage passed:

- explicit global APPROVE/REJECT;
- mandatory actor/reason;
- blocked proposal veto;
- stale analysis;
- stale proposal;
- tampered proposal evidence fingerprint;
- forbidden capability tampering;
- rejected authorization cannot materialize;
- exact authorized plan materialization;
- changed authorization hash invalidates plan;
- tampered plan edit invalidates fingerprint;
- source SHA mismatch blocks render;
- generic renderer rejects Semantic Edit Plan;
- valid semantic gate revalidates complete chain.

## Real FFmpeg end-to-end validation

Final run:

```text
33909625346
```

Result:

```text
202/202 tests PASS in 7.782 s
doctor PASS
```

New real E2E gate:

```text
test_exact_authorized_chain_renders_only_the_approved_semantic_span ... ok
```

The test:

1. creates a real 10-second MP4 with video + audio;
2. records its exact SHA-256 in a synthetic schema-v9 analysis;
3. creates a valid individual promotion approval;
4. builds a bounded proposal;
5. creates a global execution APPROVE artifact;
6. materializes a Semantic Edit Plan for exactly one 0.4-second removal;
7. executes the semantic render gate and real FFmpeg render;
8. asserts the original SHA-256 is unchanged;
9. asserts output duration is source duration minus 0.4 s within 0.15 s tolerance;
10. asserts one video stream and one audio stream remain.

This is governance/render-path evidence, not a human perceptual join-quality validation.

## CI hygiene

- workflows restored to `workflow_dispatch` only immediately after one-shot runs;
- no heavy artifacts uploaded;
- no public Release created.

## Closure decision

**Phase 2E.4: COMPLETE.**

The repository now has an explicit, stale-safe semantic execution authorization and a real FFmpeg render gate. Automatic application remains disabled.

## Next

Phase 2E.5 — Semantic Render Verification / Close-out:

- post-render structural verification;
- expected vs actual duration accounting;
- output/source stream checks;
- join-local post-render audit;
- perceptual/human evidence on rendered semantic joins;
- audit report linking analysis → approvals → proposal → authorization → plan → output;
- final decision on closing Phase 2E.
