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
- `phase2d-human-positive-closeout.md` — **2D.6 final; `CLOSE_OUT_READY`; cierre de 2D como foundation/evidence.**

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- prueba manual realizada por Guille;
- release publicable;
- seguridad perceptual general;
- autorización de corte;
- promoción al Edit Plan;
- generalización de métricas fuera del corpus evaluado.

En particular, tras 2D.6:

```text
foundation_guards_pass != safe cut
future_promotion_candidate != approved edit
safe_for_cut = false
executable = false
auto_apply = false
automatic_edits = 0
```

La promoción explícita al Edit Plan pertenece a Fase 2E.
