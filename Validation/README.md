# Validation

Esta carpeta conserva únicamente evidencia técnica y humana ligera, reproducible y auditable: hashes, provenance, decisiones y resúmenes de validación.

No usarla para almacenar vídeos, ZIPs de CI, logs voluminosos, modelos ni outputs temporales.

## Evidencia principal vigente

### Portable / ingest / analysis

- `portable-foundation-spike.md` — portable core.
- `portable-analysis-spike.md` — portable ML/análisis.
- `sync-foundation-spike.md` / `sync-hardening.md` — ingesta dual y sync.
- `spanish-large-v3-turbo-plan.md` — target Spanish.

### Fase 2

- `phase2-semantic-candidates.md` — Semantic Candidates v1.
- `phase2-semantic-protection.md` — Semantic Decisions + Protection v1.
- `phase2c-semantic-validation.md` / `phase2c-audio-backed-validation.md` — validación semántica real.
- `phase2d-correction-scope.md`, `phase2d-contextual-fillers.md`, `phase2d-join-safety.md`, `phase2d-acoustic-join.md`, `phase2d-human-acoustic-evidence.md`, `phase2d-combined-eligibility.md`, `phase2d-human-combined-eligibility.md`, `phase2d-human-positive-closeout.md` — Fase 2D.
- `phase2e-promotion-foundation.md` — 2E.1.
- `phase2e-explicit-approval-contract.md` — 2E.2.
- `phase2e-approved-plan-proposal.md` — 2E.3.
- `phase2e-execution-authorization.md` — 2E.4.
- `phase2e-post-render-closeout.md` — 2E.5 technical + human closeout.
- `phase2e-human-closeout/` — decisiones/reviews/hash manifest de 2E.5.

Fase 2E está cerrada como `CLOSE_OUT_READY`; `auto_apply=false`.

### Fase 3 — audiovisual quality / audit

- `phase3-audiovisual-quality-foundation.md` — resumen de 3.1 Quality Audit, baseline focal real, 3.2 Treatment Decision y 3.3 Normalization Profile Contract.
- `phase3-focal-quality-baseline.json` — medición persistente exacta de los tres pares ORIGINAL/RENDERED ya escuchados en 2E.5.

Runs principales:

```text
34124957783  Phase 3.1 focused + real FFmpeg E2E — 8/8 PASS
34125110506  Phase 3.1 full regression — 283/283 + doctor PASS
34134893725  focal baseline exact 2E.5 bundle — PASS
34135210344  Phase 3.2 bypass-first treatment — 14/14 PASS
34135437824  Phase 3.3 normalization profile — 13/13 PASS
```

Baseline focal observado:

```text
cases = 3
sources = 2
human perceptual PASS = 3/3
max observed |Δ integrated loudness| = 0.40 LU
max observed |Δ true peak| = 0.04 dB
```

**0.40 LU y 0.04 dB son observaciones de la muestra, no thresholds de producto.**

Interpretación acreditada hasta ahora:

- no hay evidencia para normalización obligatoria como reparación del renderer en este corpus;
- no hay evidencia para denoise por defecto;
- no hay evidencia para join smoothing/crossfade por defecto;
- `preserve` es default;
- cualquier riesgo medido sólo abre revisión;
- `ebu_r128_programme` es opt-in/review-only, no default;
- normalización ejecutable aún no está autorizada;
- `auto_apply=false`.

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- release publicable;
- generalización de seguridad/calidad fuera del corpus;
- que un número observado se convierta en threshold;
- que una medición autorice tratamiento;
- normalización, denoise o smoothing automáticos;
- validación final del ZIP portable en Windows limpio.

Cadena conceptual actual:

```text
Phase 2E output PASS
→ audiovisual_quality_audit
→ audiovisual_treatment_decision
→ normalization_profile_decision
→ [próximo: explicit normalization approval]
```

Invariantes:

```text
Phase 3 favorable signal != rescue of failed Phase 2E
measurement != treatment decision
treatment decision != treatment authorization
profile selection != normalization authorization
preserve = default
auto_apply = false
```
