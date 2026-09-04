# Validation

Esta carpeta conserva únicamente evidencia técnica ligera y reproducible: hashes, manifiestos de versiones, provenance y resúmenes de validación cuando proceda.

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

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- prueba manual realizada por Guille;
- release publicable;
- seguridad perceptual general;
- calidad natural de todos los joins renderizados;
- auto-apply semántico;
- generalización de métricas fuera del corpus evaluado.

Tras 2E.4:

```text
analysis.json                         schema v9
promotion_approval.json               schema v1
approved_edit_plan_proposal.json      schema v1
semantic_execution_authorization.json schema v1
semantic_edit_plan.json               schema v1
```

```text
individual approval != global authorization
proposal != executable Edit Plan
generic render rejects proposal
generic render rejects semantic Edit Plan
semantic render requires full-chain + source-SHA revalidation
semantic Edit Plan executable only through semantic render gate
auto_apply = false
```

Final 2E.4 evidence:

```text
33909424933  201/201 PASS + doctor
33909625346  202/202 PASS + doctor + real FFmpeg semantic E2E
```

La verificación post-render perceptual/estructural de cierre pertenece a Fase 2E.5.
