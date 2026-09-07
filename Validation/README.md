# Validation

Esta carpeta conserva únicamente evidencia técnica y humana ligera, reproducible y auditable: hashes, manifiestos de versiones, provenance, decisiones y resúmenes de validación cuando proceda.

No usarla para almacenar vídeos, ZIPs de CI, logs voluminosos, modelos ni outputs temporales.

## Evidencia principal vigente

- `portable-foundation-spike.md` — portable core.
- `portable-analysis-spike.md` — portable ML/análisis.
- `sync-foundation-spike.md` / `sync-hardening.md` — ingesta dual y sync.
- `spanish-large-v3-turbo-plan.md` — target Spanish.
- `phase2-semantic-candidates.md` — Semantic Candidates v1.
- `phase2-semantic-protection.md` — Semantic Decisions + Protection v1.
- `phase2c-semantic-validation.md` / `phase2c-audio-backed-validation.md` — validación semántica real.
- `phase2d-correction-scope.md` — 2D.1.
- `phase2d-contextual-fillers.md` — 2D.2.
- `phase2d-join-safety.md` — 2D.3.1.
- `phase2d-acoustic-join.md` / `phase2d-human-acoustic-evidence.md` — 2D.3.2/2D.3.3.
- `phase2d-combined-eligibility.md` — 2D.4.
- `phase2d-human-combined-eligibility.md` — 2D.5.
- `phase2d-human-positive-closeout.md` — 2D.6 final.
- `phase2e-promotion-foundation.md` — 2E.1 final; analysis schema v9.
- `phase2e-explicit-approval-contract.md` — 2E.2 final; individual approval schema v1.
- `phase2e-approved-plan-proposal.md` — 2E.3 final; bounded proposal schema v1.
- `phase2e-execution-authorization.md` — **2E.4 final; global authorization + Semantic Edit Plan + real FFmpeg render gate PASS.**
- `phase2e-post-render-closeout.md` — **2E.5 final; technical 3/3 + human perceptual 3/3; `CLOSE_OUT_READY`.**
- `phase2e-human-closeout/` — decisiones humanas, reviews por caso, decisión agregada y manifest final con hashes.

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. El cierre de Fase 2E no implica por sí solo:

- release publicable;
- seguridad perceptual general fuera del corpus evaluado;
- calidad natural de todos los joins posibles;
- auto-apply semántico;
- generalización de métricas fuera de la muestra;
- validación final del ZIP portable en Windows limpio.

Tras el cierre 2E.5:

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
semantic_render_verification          schema v1
semantic_render_human_review          schema v1
phase2e_closeout_decision              schema v1
```

```text
individual approval != global authorization
proposal != executable Edit Plan
generic render rejects proposal
generic render rejects semantic Edit Plan
semantic render requires full-chain + source-SHA revalidation
semantic Edit Plan executable only through semantic render gate
technical post-render PASS != human perceptual PASS
human review binds exact technical report/output/plan/join evidence
stale evidence = INVALID_EVIDENCE
auto_apply = false
```

Final 2E.4 evidence:

```text
33909424933  201/201 PASS + doctor
33909625346  202/202 PASS + doctor + real FFmpeg semantic E2E
```

Final 2E.5 evidence:

```text
34119952855  SUCCESS
278 tests PASS (13 host-only skips)
portable/provenance PASS
3 cases / 2 sources / 3 technical PASS
157 -> acoustic_context_only
298 -> acoustic_context_only
13  -> low_energy_boundary_context
3/3 human perceptual PASS
0 human FAIL
0 invalid/stale reviews
CLOSE_OUT_READY
```

Finalization hashes:

```text
source bundle manifest SHA256  d0b12929ede07c1c5a56b074008d0903a868a7cf61e5ce10801c2b682f164ed0
human decisions SHA256         867a33c87ec2154d08558a67d503535d4527cb99af07ac65458507fe73288e04
closeout decision SHA256       2cc5ae013cdcbfc53efc376d5db4f2f2f53d5a8848c019820dee6899b88c188a
```

**Fase 2E está cerrada como `CLOSE_OUT_READY`.** El siguiente bloque del roadmap es Fase 3 — calidad audiovisual/auditoría.
