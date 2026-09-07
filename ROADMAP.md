# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica/acústica temporal.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva; workflows pesados manual-only.

## Fases completadas

### Fase 0 — Bootstrap
CLI, FFmpeg/ffprobe, probe, Cleaner de silencios, Edit Plan, render y tests.

### Fase 0.5 — Technology Harvest
Repo propio, no fork. Upstreams sólo como referencias/integraciones trazables.

### Fase 1A — Portable Foundation
Core `33600174568` PASS; ML frozen `33621357438` PASS.

### Fase 1B — Ingesta dual + sincronización A/V
Master FLAC, offset +/-, drift, confidence/residual/coverage, manual override y `review_required`. Hardening `33639009841` PASS.

### Fase 1C — Transcripción + VAD sobre master
Target Spanish `33656235038`: WER `1.64%`, RTF `0.4854`, automatic edits 0.

### Fase 2A–2C
Semantic candidates, semantic protection y validación real completadas según evidencia registrada.

### Fase 2D — Scope + fillers + join safety + eligibility
**COMPLETADA COMO FOUNDATION/EVIDENCE.** Cierre humano `33894995584`: `CLOSE_OUT_READY`, 0 capacidad ejecutable.

## Fase 2E — Promotion to Edit Plan — COMPLETADA

### 2E.1 — Promotion Policy Foundation
`analysis.json` schema v9 con `promotion_assessments[]`. Final `33899201093`: 166/166 + doctor PASS.

### 2E.2 — Explicit Approval Contract
`promotion_approval.json` schema v1 separado, stale-safe y auditable. Final `33899857378`: 174/174 + doctor PASS.

### 2E.3 — Approved Edit Plan Proposal + Global Limits
`approved_edit_plan_proposal.json` schema v1, `proposed_edits[]`, no ejecutable.

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Renderer rechaza proposals explícitamente. Final `33908500929`: 186/186 + doctor PASS.

### 2E.4 — Execution Authorization / Semantic Render Gate
Cadena explícita:

```text
individual approval
→ bounded proposal
→ global execution authorization
→ semantic Edit Plan
→ semantic render gate
→ FFmpeg
```

La autorización liga analysis + proposal exactos por SHA/fingerprint. El Semantic Edit Plan sólo se materializa desde `valid_authorized`, conserva provenance exacta y exige semantic render gate. `auto_apply=false`.

```text
33909424933  201/201 PASS + doctor
33909625346  202/202 PASS + doctor + real FFmpeg E2E
```

Detalle: `Validation/phase2e-execution-authorization.md`.

### 2E.5 — Semantic Render Verification / Human Close-out — COMPLETADA

Implementado:

1. `semantic_render_verification` separado;
2. source/output SHA + protección frente a overwrite;
3. streams y duración esperada vs real;
4. auditoría acústica de cada join renderizado;
5. provenance completa analysis → approval → proposal → authorization → plan → output;
6. bundle ligero ORIGINAL/RENDERED;
7. `semantic_render_human_review` stale-safe;
8. `phase2e_closeout_decision` con thresholds precomprometidos;
9. finalizador offline que no repite ASR ni render.

Technical gate:

```text
34119952855  SUCCESS
278 tests PASS (13 host-only skips)
portable build PASS
immutable FFmpeg provenance PASS
3 cases / 2 sources
3/3 semantic renders PASS
3/3 post-render technical verification PASS
```

Human gate final:

```text
3/3 valid human perceptual PASS
0 human FAIL
0 invalid/stale reviews
status = CLOSE_OUT_READY
phase2e_closeout_ready = true
auto_apply = false
```

Casos:

```text
157  technical PASS  human PASS  acoustic_context_only
298  technical PASS  human PASS  acoustic_context_only
13   technical PASS  human PASS  low_energy_boundary_context
```

`single_pass` sigue siendo default del producto. `deterministic_overlap_12s_3s_repeat_consensus_v1` es opt-in explícito y la estrategia validada para este close-out.

Detalle: `Validation/phase2e-post-render-closeout.md` y `Validation/phase2e-human-closeout/`.

## Fase 3 — Calidad audiovisual / auditoría — SIGUIENTE

Objetivo: elevar la calidad audiovisual del output ya autorizado/renderizado sin debilitar la semántica ni la auditabilidad.

Ámbitos previstos:

1. join treatment audiovisual conservador;
2. normalización controlada;
3. denoise controlado cuando aporte valor medible;
4. auditoría avanzada de joins y continuidad A/V;
5. informe end-to-end de calidad;
6. preservar originales, provenance y reversibilidad;
7. mantener `auto_apply=false` hasta nueva evidencia específica.

No anticipar UX ni release hardening dentro de esta fase.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, preparar proposal, autorizar globalmente, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. limpiar tooling diagnóstico 2E que ya no deba permanecer;
2. revisar diff completo de `phase2e-post-render-verification` contra `main`;
3. ejecutar gate final ligero/regresión adecuada si procede;
4. integrar Fase 2E cerrada en `main`;
5. abrir rama limpia para Fase 3;
6. comenzar calidad audiovisual/auditoría sin habilitar `auto_apply`.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
