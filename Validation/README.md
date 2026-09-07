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

- `phase3-audiovisual-quality-foundation.md` — 3.1 Quality Audit, baseline focal real, 3.2 Treatment Decision y 3.3 Normalization Profile Contract.
- `phase3-focal-quality-baseline.json` — medición persistente exacta de los tres pares ORIGINAL/RENDERED ya escuchados en 2E.5.
- `phase3-normalization-foundation.md` — 3.4 Explicit Normalization Approval + 3.5a–d plan/authorization/renderer/post-render technical verification.
- `phase3-noise-audit-foundation.md` — 3.6a Noise Evidence Audit measurement-only.

Runs principales:

```text
34124957783  Phase 3.1 focused + real FFmpeg E2E — 8/8 PASS
34125110506  Phase 3.1 full regression — 283/283 + doctor PASS
34134893725  focal baseline exact 2E.5 bundle — PASS
34135210344  Phase 3.2 bypass-first treatment — 14/14 PASS
34135437824  Phase 3.3 normalization profile — 13/13 PASS
34136124997  Phase 3.4 explicit normalization approval — 15/15 PASS
34136621557  Phase 3.5a plan proposal base gate — 15/15 PASS
34138226442  Phase 3.5b execution authorization — 15/15 PASS
34139056626  Phase 3.5c gated linear render — 25/25 + real FFmpeg E2E PASS
34139502187  Phase 3.5d independent post-render verification — 16/16 + real FFmpeg E2E PASS
34139639280  full regression through 3.5d — 337/337 + doctor PASS
34141013261  Phase 3.6a noise evidence audit — 9/9 + real MP4/AAC E2E PASS
34141115293  full regression through 3.6a — 346/346 + doctor PASS
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

- no hay evidencia para normalización obligatoria como reparación del renderer en el corpus focal;
- existe una vía `ebu_r128_programme` opt-in técnicamente validada y fail-closed;
- la normalización sigue pendiente de human perceptual close-out antes de generalizarla;
- `noise_evidence_audit` puede medir energía speech/non-speech con timing evidence explícita y SHA vigente;
- cobertura insuficiente se distingue de un problema de ruido;
- digital silence no recibe un floor dBFS inventado;
- ninguna métrica 3.6a selecciona ni autoriza denoise;
- no hay evidencia para denoise por defecto;
- no hay evidencia para join smoothing/crossfade por defecto;
- `preserve` es default;
- `auto_apply=false`.

## Regla de interpretación

Una validación PASS acredita únicamente el alcance descrito en su documento. No implica por sí sola:

- release publicable;
- generalización de seguridad/calidad fuera del corpus;
- que un número observado se convierta en threshold;
- que una medición autorice tratamiento;
- que technical normalization PASS equivalga a human perceptual PASS;
- que un dBFS medido implique necesidad de denoise;
- denoise o smoothing automáticos;
- validación final del ZIP portable en Windows limpio.

Cadena conceptual actual:

```text
Phase 2E output PASS
→ audiovisual_quality_audit
   ├→ audiovisual_treatment_decision
   │  → normalization_profile_decision
   │  → normalization_approval
   │  → normalization_plan_proposal
   │  → normalization_execution_authorization
   │  → normalization_render_result
   │  → normalization_post_render_verification
   │  → human perceptual normalization review (PENDING)
   └→ noise_evidence_audit
      → denoise evaluation corpus (NEXT)
```

Invariantes:

```text
Phase 3 favorable signal != rescue of failed Phase 2E
measurement != treatment decision
treatment decision != treatment authorization
noise measurement != denoise decision
denoise decision != denoise authorization
profile selection != normalization authorization
technical PASS != human perceptual PASS
preserve = default
auto_apply = false
```
