# ROADMAP — Video_Tunner

## Principios

- Windows 10/11 x64 portable: ZIP → descomprimir → ejecutar.
- Vídeo con audio embebido o vídeo + audio externo.
- Master audio y sincronización antes de transcripción/VAD/semántica/acústica temporal.
- Originales intactos y decisiones auditables/reversibles.
- Ante baja confianza: REVIEW/manual, no adivinar.
- CI pesada sólo cuando aporta evidencia nueva.

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

## Fase 2 — Cleaner inteligente — EN CURSO

### 2D — Scope + fillers + join safety + eligibility — COMPLETADA COMO FOUNDATION/EVIDENCE

Cierre humano `33894995584`: `CLOSE_OUT_READY`, 0 capacidad ejecutable.

### 2E — Promotion to Edit Plan — EN CURSO

#### 2E.1 — Promotion Policy Foundation — COMPLETADA

`analysis.json` schema v9 con `promotion_assessments[]`. Sólo `possible_repetition` respaldada inicialmente. Final `33899201093`: 166/166 + doctor PASS.

#### 2E.2 — Explicit Approval Contract — COMPLETADA

`promotion_approval.json` schema v1 separado, stale-safe y auditable. Final `33899857378`: 174/174 + doctor PASS.

#### 2E.3 — Approved Edit Plan Proposal + Global Limits — COMPLETADA

`approved_edit_plan_proposal.json` schema v1, `proposed_edits[]`, no ejecutable.

Límites precomprometidos:

```text
max_semantic_edits    = 10
max_removed_seconds   = 30.0
max_removed_fraction  = 0.05
```

Renderer rechaza proposals explícitamente. Final `33908500929`: 186/186 + doctor PASS.

#### 2E.4 — Execution Authorization / Semantic Render Gate — COMPLETADA

Nueva cadena explícita:

```text
individual approval
→ bounded proposal
→ global execution authorization
→ semantic Edit Plan
→ semantic render gate
→ FFmpeg
```

Artefactos nuevos:

```text
semantic_execution_authorization.json  schema v1
semantic_edit_plan.json                schema v1
```

La autorización global liga analysis + proposal exactos por SHA-256 y fingerprint, exige actor/reason/timestamp y puede quedar stale si cambia cualquier evidencia.

El Semantic Edit Plan sólo se materializa desde `valid_authorized`, conserva provenance exacta y plan fingerprint, es `executable=true` pero `auto_apply=false` y exige semantic render gate.

El renderer genérico rechaza Semantic Edit Plans; la única vía pública es `execution render`, que revalida source + cadena completa justo antes de FFmpeg.

Validación:

```text
33909424933  201/201 PASS en 7.310 s + doctor
33909625346  202/202 PASS en 7.782 s + doctor + real FFmpeg E2E
```

E2E final:
- MP4 real de 10 s;
- un único edit autorizado de 0.4 s;
- original SHA-256 intacto;
- output duration esperada ±0.15 s;
- vídeo+audio preservados.

Detalle: `Validation/phase2e-execution-authorization.md`.

#### 2E.5 — Semantic Render Verification / Close-out — SIGUIENTE

Objetivo: no basta con que FFmpeg renderice; hay que demostrar que el output resultante cumple estructural y perceptualmente.

Orden:

1. crear post-render verification report separado;
2. comprobar source/output SHA y evitar overwrite;
3. verificar streams esperados;
4. comparar duración esperada vs real por Edit Plan;
5. auditar cada join renderizado con ventanas antes/después;
6. medir discontinuidades post-render y no sólo pre-render;
7. crear evidencia perceptual/humana sobre joins semánticos reales;
8. conservar provenance completa analysis → approval → proposal → authorization → plan → output;
9. fail-safe si post-render verification falla;
10. decidir formalmente si Fase 2E puede cerrarse.

## Fase 3 — Calidad audiovisual / auditoría
Normalización, join treatment, denoise controlado, join audit avanzado e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, preparar proposal, autorizar globalmente, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. integrar 2E.4 en `main` con workflow manual-only;
2. crear rama limpia para 2E.5;
3. post-render structural verification;
4. post-render join audit;
5. evidencia humana/perceptual antes de cerrar 2E;
6. mantener auto-apply semántico deshabilitado hasta ese cierre.
