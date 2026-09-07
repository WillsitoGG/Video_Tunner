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

Artefactos:

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

Detalle: `Validation/phase2e-execution-authorization.md`.

#### 2E.5 — Semantic Render Verification / Close-out — TECHNICAL PRE-HUMAN GATE PASS

Ya implementado y validado técnicamente:

1. `semantic_render_verification` separado;
2. source/output SHA y protección frente a overwrite;
3. streams esperados;
4. duración esperada vs real por Semantic Edit Plan;
5. auditoría de cada join sobre el output renderizado;
6. clasificación acústica post-render;
7. provenance completa analysis → approval → proposal → authorization → plan → output;
8. bundle ligero de escucha ORIGINAL/RENDERED;
9. `semantic_render_human_review` stale-safe;
10. agregación `phase2e_closeout_decision` con thresholds precomprometidos;
11. finalizador offline que no repite ASR ni render.

Evidencia técnica final:

```text
34119952855  SUCCESS
278 tests PASS (13 host-only skips)
portable build PASS
immutable FFmpeg provenance PASS
3 precommitted AMI cases / 2 sources
3/3 semantic renders PASS
3/3 post-render technical verification PASS
```

Casos:

```text
157  PASS  acoustic_context_only
298  PASS  acoustic_context_only
13   PASS  low_energy_boundary_context
```

Estado real:

```text
technical pre-human gate = PASS
human perceptual reviews = 0/3 PENDING
Phase 2E close-out = NOT YET READY
```

El último gate no se automatiza: Guille debe escuchar los tres pares ORIGINAL/RENDERED y emitir PASS/FAIL real por join. Sólo 3/3 PASS válidos en las dos fuentes producen `CLOSE_OUT_READY`; un único FAIL produce `INSUFFICIENT_JOIN_QUALITY`. Evidencia stale/alterada produce `INVALID_EVIDENCE`.

`single_pass` sigue siendo default del producto. `deterministic_overlap_12s_3s_repeat_consensus_v1` es opt-in explícito y la estrategia validada para este close-out.

Detalle: `Validation/phase2e-post-render-closeout.md`.

## Fase 3 — Calidad audiovisual / auditoría

**NO INICIAR hasta cerrar 2E.5.**

Después del `CLOSE_OUT_READY` humano: normalización, join treatment, denoise controlado, join audit avanzado e informe.

## Fase 4 — UX mínima
Seleccionar vídeo, audio externo opcional, sync, analizar, revisar, aprobar/rechazar, preparar proposal, autorizar globalmente, renderizar y abrir outputs.

## Fase 5 — Portable Release Hardening
Build Windows limpia, ZIP final, digests, manifest, licencias/notices, estrategia final de modelos y zero-install/offline.

## Fase 6 — Extras
Subtítulos visuales, reframe, zooms, shorts, B-roll y extras después del Cleaner fiable.

## Orden inmediato

1. Guille escucha los tres pares ORIGINAL/RENDERED del bundle técnico `34119952855`;
2. registrar PASS/FAIL + motivo real para cada `join_id`;
3. ejecutar `.github/scripts/finalize_phase2e_human_closeout.py` offline contra el bundle inmutable;
4. si `CLOSE_OUT_READY`: documentar cierre 2E.5/2E;
5. limpiar workflows/scripts diagnósticos que ya no sean permanentes;
6. revisar diff completo, preparar PR e integrar 2E.5 en `main`;
7. sólo entonces abrir Fase 3.

No relajar thresholds post hoc y no publicar Release sin autorización expresa de Guille.
