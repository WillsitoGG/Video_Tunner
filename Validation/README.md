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
- `phase2d-human-positive-closeout.md` — 2D.6 final; cierre de 2D como foundation/evidence.
- `phase2e-promotion-foundation.md` — 2E.1 final; analysis schema v9.
- `phase2e-explicit-approval-contract.md` — 2E.2 final; approval schema v1.
- `phase2e-approved-plan-proposal.md` — **2E.3 final; proposal schema v1, global limits y renderer isolation PASS.**

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- prueba manual realizada por Guille;
- release publicable;
- seguridad perceptual general;
- autorización global de Edit Plan;
- autorización de render semántico;
- auto-apply;
- generalización de métricas fuera del corpus evaluado.

Tras 2E.3:

```text
analysis.json = schema v9
promotion_approval.json = schema v1
approved_edit_plan_proposal.json = schema v1
valid_approved approval != Edit Plan authorization
proposal_ready_for_global_review != render authorization
proposed_edits[] != edits[]
requires_global_review = true
globally_approved = false
render_authorization = false
executable = false
auto_apply = false
automatic_edits = 0
```

El renderer rechaza explícitamente proposals no ejecutables. La autorización global y materialización de un Edit Plan ejecutable pertenecen a Fase 2E.4.
